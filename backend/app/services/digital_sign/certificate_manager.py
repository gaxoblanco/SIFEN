"""
Gestor de certificados digitales para SIFEN
Cumple con las especificaciones del Manual Técnico v150 - VERSIÓN CORREGIDA
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, Dict, Any, List, Union
from cryptography import x509
from cryptography.x509.oid import ExtensionOID, ExtendedKeyUsageOID, NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.asymmetric import rsa
from .config import CertificateConfig


class CertificateManager:
    """Gestor de certificados digitales según especificaciones SIFEN v150"""

    def __init__(self, config: CertificateConfig):
        self.config = config
        self._certificate: Optional[x509.Certificate] = None
        self._private_key: Optional[rsa.RSAPrivateKey] = None

    def load_certificate(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Carga el certificado y clave privada desde archivo PFX"""
        try:
            with open(self.config.cert_path, "rb") as f:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    f.read(),
                    self.config.cert_password.encode()
                )

                if not certificate or not private_key:
                    raise ValueError(
                        "No se pudo cargar el certificado o la clave privada")

                # Verificar que private_key sea RSAPrivateKey
                if not isinstance(private_key, rsa.RSAPrivateKey):
                    raise ValueError("La clave privada debe ser RSA")

                self._certificate = certificate
                self._private_key = private_key
                return certificate, private_key

        except FileNotFoundError:
            raise ValueError("Certificado no encontrado")
        except Exception as e:
            raise ValueError(f"Error al cargar el certificado: {str(e)}")

    def validate_certificate(self) -> bool:
        """Valida que el certificado sea válido y no esté expirado"""
        if not self._certificate:
            try:
                self.load_certificate()
            except Exception:
                return False

            if not self._certificate:
                return False

        # Manejar timezone correctamente
        now = datetime.now(timezone.utc)
        not_valid_after = self._certificate.not_valid_after

        # Si el certificado no tiene timezone, asumir UTC
        if not_valid_after.tzinfo is None:
            not_valid_after = not_valid_after.replace(tzinfo=timezone.utc)

        return not_valid_after > now

    def check_expiry(self) -> Tuple[bool, timedelta]:
        """Verifica si el certificado está próximo a expirar"""
        if not self._certificate:
            self.load_certificate()

        if not self._certificate:
            raise ValueError("Certificado no cargado")

        # Usar timezone-aware datetimes
        now = datetime.now(timezone.utc)
        not_valid_after = self._certificate.not_valid_after

        if not_valid_after.tzinfo is None:
            not_valid_after = not_valid_after.replace(tzinfo=timezone.utc)

        days_left = not_valid_after - now
        is_expiring = days_left.days <= self.config.cert_expiry_days

        return is_expiring, days_left

    @property
    def certificate(self) -> x509.Certificate:
        """Retorna el certificado cargado"""
        if not self._certificate:
            self.load_certificate()

        if not self._certificate:
            raise ValueError("No se pudo cargar el certificado")
        return self._certificate

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        """Retorna la clave privada cargada"""
        if not self._private_key:
            self.load_certificate()

        if not self._private_key:
            raise ValueError("No se pudo cargar la clave privada")
        return self._private_key

    def get_certificate_info(self) -> Dict[str, Any]:
        """Obtiene información completa del certificado compatible con SIFEN"""
        if not self._certificate:
            self.load_certificate()

        if not self._certificate:
            raise ValueError("No se pudo cargar el certificado")

        cert = self._certificate

        # Extraer RUC del certificado según especificaciones SIFEN
        ruc_emisor = self._extract_ruc_from_certificate(cert)

        return {
            'serial_number': str(cert.serial_number),
            'issuer': cert.issuer.rfc4514_string(),
            'subject': cert.subject.rfc4514_string(),
            'not_valid_before': cert.not_valid_before,
            'not_valid_after': cert.not_valid_after,
            'signature_algorithm': cert.signature_algorithm_oid._name,
            'version': cert.version.name,
            'extensions': self._get_extensions_info(cert),
            'public_key_info': self._get_public_key_info(cert.public_key()),
            'thumbprint_sha1': self.get_certificate_thumbprint('sha1'),
            'thumbprint_sha256': self.get_certificate_thumbprint('sha256'),
            'is_valid': self.validate_certificate(),
            'days_until_expiry': (cert.not_valid_after - datetime.now(timezone.utc)).days,
            'ruc_emisor': ruc_emisor,
            'es_persona_juridica': self._is_persona_juridica(),
            'psc_habilitado': self._is_psc_authorized()
        }

    def get_private_key(self) -> rsa.RSAPrivateKey:
        """Obtiene la clave privada"""
        return self.private_key

    def get_certificate(self) -> x509.Certificate:
        """Obtiene el certificado X509"""
        return self.certificate

    def get_certificate_serial(self) -> str:
        """Obtiene el número de serie del certificado"""
        cert = self.certificate
        return str(cert.serial_number)

    def get_certificate_issuer(self) -> str:
        """Obtiene el emisor del certificado"""
        cert = self.certificate
        return cert.issuer.rfc4514_string()

    def get_certificate_subject(self) -> str:
        """Obtiene el sujeto del certificado"""
        cert = self.certificate
        return cert.subject.rfc4514_string()

    def get_certificate_validity(self) -> Dict[str, datetime]:
        """Obtiene las fechas de validez del certificado"""
        cert = self.certificate

        return {
            'not_valid_before': cert.not_valid_before,
            'not_valid_after': cert.not_valid_after
        }

    def get_certificate_extensions(self) -> List[Dict[str, Any]]:
        """Obtiene las extensiones del certificado"""
        cert = self.certificate
        return self._get_extensions_info(cert)

    def get_certificate_public_key(self) -> Dict[str, Any]:
        """Obtiene información de la clave pública del certificado"""
        cert = self.certificate
        return self._get_public_key_info(cert.public_key())

    def get_certificate_thumbprint(self, algorithm: str = 'sha256') -> str:
        """Obtiene el hash/thumbprint del certificado"""
        cert = self.certificate
        cert_bytes = cert.public_bytes(serialization.Encoding.DER)

        digest: hashes.Hash
        if algorithm.lower() == 'sha1':
            digest = hashes.Hash(hashes.SHA1())
        elif algorithm.lower() == 'sha256':
            digest = hashes.Hash(hashes.SHA256())
        elif algorithm.lower() == 'md5':
            digest = hashes.Hash(hashes.MD5())
        else:
            raise ValueError(f"Algoritmo de hash no soportado: {algorithm}")

        digest.update(cert_bytes)
        hash_bytes = digest.finalize()

        return hash_bytes.hex().upper()

    def _get_extensions_info(self, cert: x509.Certificate) -> List[Dict[str, Any]]:
        """Obtiene información detallada de las extensiones del certificado"""
        extensions_info = []

        for ext in cert.extensions:
            ext_info = {
                'oid': ext.oid.dotted_string,
                'name': getattr(ext.oid, '_name', 'Unknown'),
                'critical': ext.critical
            }

            # Procesar extensiones específicas importantes para SIFEN
            try:
                if isinstance(ext.value, x509.SubjectAlternativeName):
                    # Manejar SAN de forma segura
                    san_values = []
                    for name in ext.value:
                        try:
                            if hasattr(name, 'value'):
                                san_values.append(str(name.value))
                            else:
                                san_values.append(str(name))
                        except Exception as e:
                            san_values.append(f"Error: {str(e)}")
                    ext_info['value'] = san_values

                elif isinstance(ext.value, x509.KeyUsage):
                    # Manejar KeyUsage de forma segura
                    key_usage = {}
                    for usage in ['digital_signature', 'key_encipherment', 'data_encipherment',
                                  'key_agreement', 'key_cert_sign', 'crl_sign', 'content_commitment',
                                  'encipher_only', 'decipher_only']:
                        try:
                            key_usage[usage] = getattr(ext.value, usage, False)
                        except Exception:
                            key_usage[usage] = False
                    ext_info['value'] = key_usage

                elif isinstance(ext.value, x509.ExtendedKeyUsage):
                    # Manejar ExtendedKeyUsage de forma segura
                    try:
                        ext_info['value'] = [
                            usage.dotted_string for usage in ext.value]
                    except Exception:
                        ext_info['value'] = [
                            "Error procesando ExtendedKeyUsage"]

                elif isinstance(ext.value, x509.BasicConstraints):
                    ext_info['value'] = {
                        'ca': ext.value.ca,
                        'path_length': ext.value.path_length
                    }
                else:
                    # Para otros tipos, convertir a string de forma segura
                    try:
                        ext_info['value'] = str(ext.value)
                    except Exception as e:
                        ext_info['value'] = f"Error: {str(e)}"

            except Exception as e:
                ext_info['value'] = f"Error procesando extensión: {str(e)}"

            extensions_info.append(ext_info)

        return extensions_info

    def _get_public_key_info(self, public_key: Any) -> Dict[str, Any]:
        """Obtiene información de la clave pública"""
        key_info: Dict[str, Any] = {
            'algorithm': type(public_key).__name__
        }

        if isinstance(public_key, rsa.RSAPublicKey):
            key_info.update({
                'key_size': public_key.key_size,
                'public_exponent': public_key.public_numbers().e,
                'modulus_size': public_key.key_size
            })

        # Serializar la clave pública
        try:
            pem_data = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            key_info['pem'] = pem_data.decode('utf-8')
        except Exception as e:
            key_info['pem_error'] = str(e)

        return key_info

    def _extract_ruc_from_certificate(self, cert: x509.Certificate) -> Optional[str]:
        """Extrae el RUC del certificado según especificaciones SIFEN v150"""
        try:
            # 1. Buscar en SerialNumber (Persona Jurídica)
            subject = cert.subject
            for attribute in subject:
                if attribute.oid == NameOID.SERIAL_NUMBER:
                    serial_value = attribute.value.strip()
                    # Validar si es un RUC válido (con o sin prefijo)
                    ruc = self._normalize_and_validate_ruc(serial_value)
                    if ruc:
                        return ruc

            # 2. Buscar en SubjectAlternativeName (Persona Física)
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )

                for name in san_ext.value:
                    # Manejar diferentes tipos de SAN
                    name_value = None

                    if hasattr(name, 'value'):
                        name_value = str(name.value)
                    elif hasattr(name, 'bytes'):
                        name_value = name.bytes.decode(
                            'utf-8', errors='ignore')
                    else:
                        name_value = str(name)

                    if name_value:
                        ruc = self._normalize_and_validate_ruc(name_value)
                        if ruc:
                            return ruc

            except x509.ExtensionNotFound:
                pass
            except Exception as e:
                # Log pero no fallar
                print(f"Warning: Error procesando SubjectAlternativeName: {e}")

            return None
        except Exception as e:
            print(f"Error extrayendo RUC del certificado: {e}")
            return None

    def _normalize_and_validate_ruc(self, value: str) -> Optional[str]:
        """Normaliza y valida un valor RUC, retornando formato completo si es válido"""
        if not value:
            return None

        # Limpiar espacios
        cleaned = value.strip()

        # Determinar si tiene prefijo RUC
        has_ruc_prefix = cleaned.upper().startswith('RUC')

        if has_ruc_prefix:
            # Extraer solo la parte numérica para validación
            numeric_part = cleaned[3:].strip()
            if self._validate_ruc_format(numeric_part):
                return cleaned.upper()  # Retornar formato completo normalizado
        else:
            # No tiene prefijo, validar directamente
            if self._validate_ruc_format(cleaned):
                return f"RUC{cleaned}"  # Retornar con prefijo agregado

        return None

    def _validate_ruc_format(self, ruc: str) -> bool:
        """Valida formato RUC Paraguay: XXXXXXXX-X (sin prefijo RUC)"""
        if not ruc or '-' not in ruc:
            return False

        parts = ruc.split('-')
        if len(parts) != 2:
            return False

        base, dv = parts

        # Validar formato: 8 dígitos + 1 dígito verificador
        if len(base) != 8 or not base.isdigit():
            return False

        if len(dv) != 1 or not dv.isdigit():
            return False

        # Validar dígito verificador (algoritmo módulo 11)
        return self._validate_ruc_checksum(base, dv)

    def _validate_ruc_checksum(self, base: str, dv: str) -> bool:
        """Valida el dígito verificador del RUC usando módulo 11"""
        try:
            print(f"🔍 Validando RUC: base={base}, dv={dv}")  # Debug temporal

            # Factores para el cálculo
            factors = [2, 3, 4, 5, 6, 7, 2, 3]

            # Calcular suma ponderada
            total = sum(int(digit) * factor for digit,
                        factor in zip(base, factors))
            print(f"🔍 Total ponderado: {total}")  # Debug temporal

            # Calcular módulo 11
            remainder = total % 11
            print(f"🔍 Remainder: {remainder}")  # Debug temporal

            # Calcular dígito verificador
            if remainder < 2:
                calculated_dv = 0
            else:
                calculated_dv = 11 - remainder

            # Debug temporal
            print(f"🔍 DV calculado: {calculated_dv}, DV esperado: {dv}")

            result = str(calculated_dv) == dv
            print(f"🔍 Resultado validación: {result}")  # Debug temporal

            return result
        except Exception as e:
            print(f"🔍 Error en validación: {e}")  # Debug temporal
            return False

    def _is_persona_juridica(self) -> bool:
        """Determina si el certificado es de persona jurídica"""
        if not self._certificate:
            return False

        # Para persona jurídica el RUC está en SerialNumber
        subject = self._certificate.subject
        for attribute in subject:
            if attribute.oid == NameOID.SERIAL_NUMBER:
                return attribute.value.startswith('RUC')
        return False

    def _is_psc_authorized(self) -> bool:
        """Verifica si el PSC está habilitado según SIFEN"""
        if not self._certificate:
            return False

        issuer = self._certificate.issuer.rfc4514_string()
        return self._is_psc_authorized_detailed(issuer)

    def _is_psc_authorized_detailed(self, issuer: str) -> bool:
        """Verifica si el PSC está en la lista de autorizados por SET"""
        # Lista actualizada de PSCs autorizados en Paraguay
        authorized_pscs = [
            "AC Raíz Paraguay",
            "Subsecretaría de Estado de Tributación",
            "SET",
            "PSC Paraguay",
            "Autoridad Certificadora de Paraguay",
            # Agregar más según lista oficial SET
        ]

        issuer_lower = issuer.lower()
        return any(
            psc.lower() in issuer_lower
            for psc in authorized_pscs
        )

    def validate_for_sifen(self) -> Dict[str, Any]:
        """Valida el certificado específicamente para cumplir con SIFEN v150"""
        if not self._certificate:
            try:
                self.load_certificate()
            except Exception as e:
                return {
                    'valid': False,
                    'errors': [f'No se pudo cargar el certificado: {str(e)}'],
                    'warnings': []
                }

        cert = self._certificate
        if cert is None:  # Type guard adicional
            return {
                'valid': False,
                'errors': ['Certificado no disponible'],
                'warnings': []
            }
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Validación 1: Certificado vigente
        if not self.validate_certificate():
            validation_result['valid'] = False
            validation_result['errors'].append(
                'Certificado expirado o no válido')

        # Validación 2: RUC del emisor (CRÍTICO para SIFEN)
        ruc = self._extract_ruc_from_certificate(cert)
        if not ruc:
            validation_result['valid'] = False
            validation_result['errors'].append(
                'No se encontró RUC en el certificado')
        elif not self._validate_ruc_format(ruc):
            validation_result['valid'] = False
            validation_result['errors'].append(
                f'Formato de RUC inválido: {ruc}')

        # Validación 3: Algoritmo y tamaño de clave
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            key_size = public_key.key_size
            if key_size not in [2048, 4096]:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f'Tamaño de clave RSA no válido: {key_size} bits. '
                    'SIFEN requiere 2048 o 4096 bits.'
                )
        else:
            validation_result['valid'] = False
            validation_result['errors'].append(
                'SIFEN requiere certificados con clave RSA')

        # Validación 4: KeyUsage - firma digital obligatoria
        try:
            ku_ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.KEY_USAGE)
            if not getattr(ku_ext.value, 'digital_signature', False):
                validation_result['valid'] = False
                validation_result['errors'].append(
                    'KeyUsage debe incluir "digital_signature"')
        except x509.ExtensionNotFound:
            validation_result['valid'] = False
            validation_result['errors'].append(
                'Extensión KeyUsage requerida no encontrada')

        # Validación 5: ExtendedKeyUsage para TLS
        try:
            eku_ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.EXTENDED_KEY_USAGE)
            has_client_auth = any(
                usage == ExtendedKeyUsageOID.CLIENT_AUTH
                for usage in eku_ext.value
            )
            if not has_client_auth:
                validation_result['warnings'].append(
                    'Sin clientAuth en ExtendedKeyUsage (necesario para transmisión TLS)'
                )
        except x509.ExtensionNotFound:
            validation_result['warnings'].append(
                'Sin extensión ExtendedKeyUsage')

        # Validación 6: Issuer (PSC autorizado)
        issuer = cert.issuer.rfc4514_string()
        if not self._is_psc_authorized_detailed(issuer):
            validation_result['warnings'].append(
                f'PSC emisor no reconocido: {issuer}'
            )

        # Validación 7: Proximidad a expiración
        try:
            is_expiring, days_left = self.check_expiry()
            if is_expiring:
                validation_result['warnings'].append(
                    f'Certificado expira en {days_left.days} días'
                )
        except Exception:
            pass

        return validation_result

    def export_certificate_pem(self) -> str:
        """Exporta el certificado en formato PEM"""
        cert = self.certificate
        return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    def export_private_key_pem(self, password: Optional[str] = None) -> str:
        """Exporta la clave privada en formato PEM"""
        key = self.private_key

        encryption_algorithm: serialization.KeySerializationEncryption
        if password:
            encryption_algorithm = serialization.BestAvailableEncryption(
                password.encode())
        else:
            encryption_algorithm = serialization.NoEncryption()

        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_algorithm
        ).decode('utf-8')
