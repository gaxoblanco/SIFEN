SIFEN v150 XSD Schemas - Paraguay Electronic Invoice System
🎯 Quick Reference

Sistema: SIFEN (Sistema Integrado de Facturación Electrónica Nacional)
Version: 150 (Sept 2019)
Namespace: http://ekuatia.set.gov.py/sifen/xsd
Encoding: UTF-8
Official URL: http://ekuatia.set.gov.py/sifen/xsd
🚀 Essential Schemas for Development
Core Document Schema

xml

<!-- PRIMARY SCHEMA - All electronic documents -->
DE_v150.xsd                    // Main schema for all document types
├── Factura Electrónica (FE)
├── Autofactura Electrónica (AFE)  
├── Nota de Crédito (NCE)
├── Nota de Débito (NDE)
└── Nota de Remisión (NRE)

Web Service Schemas

xml

<!-- INDIVIDUAL DOCUMENT SUBMISSION -->
siRecepDE_v150.xsd            // Send single document
resRecepDE_v150.xsd           // Response for single document
ProtProcesDE_v150.xsd         // Processing protocol

<!-- BATCH SUBMISSION (up to 50 docs) -->
SiRecepLoteDE_v150.xsd        // Send batch
resRecepLoteDE_v150.xsd       // Batch response
ProtProcesLoteDE_v150.xsd     // Batch processing protocol
SiResultLoteDE_v150.xsd       // Query batch results
resResultLoteDE_v150.xsd      // Batch results response

Digital Signature

xml

xmldsig-core-schema-v150.xsd  // W3C XML Digital Signature standard

📋 Complete Schema Catalog

Schema	Type	Purpose	Implementation Priority
DE_v150.xsd	Core	All electronic documents	🔴 Critical
siRecepDE_v150.xsd	WS Request	Single document submission	🔴 Critical
resRecepDE_v150.xsd	WS Response	Single document response	🔴 Critical
xmldsig-core-schema-v150.xsd	Security	Digital signature	🔴 Critical
SiRecepLoteDE_v150.xsd	WS Request	Batch submission	🟡 High
resRecepLoteDE_v150.xsd	WS Response	Batch response	🟡 High
ProtProcesDE_v150.xsd	Protocol	Processing protocol	🟡 High
ProtProcesLoteDE_v150.xsd	Protocol	Batch processing	🟡 High
SiResultLoteDE_v150.xsd	WS Request	Query batch results	🟡 High
resResultLoteDE_v150.xsd	WS Response	Batch results	🟡 High
siConsDE_v150.xsd	WS Request	Query document by CDC	🟢 Medium
resConsDE_v150.xsd	WS Response	Document query response	🟢 Medium
siConsRUC_v150.xsd	WS Request	Query RUC info	🟢 Medium
resConsRUC_v150.xsd	WS Response	RUC query response	🟢 Medium
siRecepEvento_v150.xsd	WS Request	Register events	🟢 Medium
resRecepEvento_v150.xsd	WS Response	Event registration response	🟢 Medium
ContenedorDE_v150.xsd	Container	Document container	🔵 Low
ContenedorEvento_v150.xsd	Container	Event container	🔵 Low
ContenedorRUC_v150.xsd	Container	RUC container	🔵 Low
Evento_v150.xsd	Events	Event format	🔵 Low

🛠️ Development Implementation Guide
Phase 1: Core Implementation

typescript

// Essential schemas for basic functionality
const CORE_SCHEMAS = [
  'DE_v150.xsd',                    // Document structure
  'siRecepDE_v150.xsd',            // Send documents
  'resRecepDE_v150.xsd',           // Receive responses
  'xmldsig-core-schema-v150.xsd'   // Digital signatures
];

Phase 2: Batch Processing

typescript

// Add batch capabilities
const BATCH_SCHEMAS = [
  'SiRecepLoteDE_v150.xsd',        // Send batches
  'resRecepLoteDE_v150.xsd',       // Batch responses
  'SiResultLoteDE_v150.xsd',       // Query results
  'resResultLoteDE_v150.xsd'       // Results response
];

Phase 3: Query & Events

typescript

// Add query and event management
const EXTENDED_SCHEMAS = [
  'siConsDE_v150.xsd',             // Document queries
  'siConsRUC_v150.xsd',            // RUC queries
  'siRecepEvento_v150.xsd'         // Event management
];

🔧 Technical Implementation Notes
Namespace Declaration

xml

<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd">

Version Control

    Current: v150
    Format: [SchemaName]_v150.xsd
    Compatibility: Only current version accepted
    Updates: Breaking changes require system updates

Validation Requirements

typescript

// Mandatory validation before transmission
const validateBeforeSend = {
  schema: 'DE_v150.xsd',
  encoding: 'UTF-8',
  digitalSignature: true,
  namespaceCheck: true
};

📊 Document Types & Schemas Mapping

Document Type	Spanish Name	Schema Coverage	Use Case
FE	Factura Electrónica	DE_v150.xsd	Standard invoice
AFE	Autofactura Electrónica	DE_v150.xsd	Self-billing
NCE	Nota de Crédito	DE_v150.xsd	Credit note
NDE	Nota de Débito	DE_v150.xsd	Debit note
NRE	Nota de Remisión	DE_v150.xsd	Delivery note

🌐 Web Service Endpoints
Production

https://sifen.set.gov.py/de/ws/sync/recibe.wsdl
https://sifen.set.gov.py/de/ws/async/recibe-lote.wsdl
https://sifen.set.gov.py/de/ws/consultas/consulta.wsdl

Testing

https://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl
https://sifen-test.set.gov.py/de/ws/async/recibe-lote.wsdl
https://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl

⚡ Cursor AI Optimization Tags

typescript

// AI Context Tags for better code assistance
#SIFEN #Paraguay #ElectronicInvoice #XSD #WebServices
#DigitalSignature #XML #TaxCompliance #Integration

// Schema categories for AI understanding
interface SIFENSchemas {
  core: 'DE_v150.xsd';
  webServices: {
    individual: ['siRecepDE_v150.xsd', 'resRecepDE_v150.xsd'];
    batch: ['SiRecepLoteDE_v150.xsd', 'resRecepLoteDE_v150.xsd'];
    query: ['siConsDE_v150.xsd', 'siConsRUC_v150.xsd'];
    events: ['siRecepEvento_v150.xsd', 'Evento_v150.xsd'];
  };
  security: 'xmldsig-core-schema-v150.xsd';
}

🚨 Critical Implementation Requirements

    Digital Signature: All documents MUST be digitally signed
    Schema Validation: Validate against XSD before transmission
    Version Control: Only v150 schemas accepted
    Encoding: UTF-8 mandatory
    Namespace: Exact namespace URI required
    TLS: v1.2 with mutual authentication
    Certificate: Valid PSC-issued digital certificate required

📞 Support & Resources

    Official Documentation: Manual Técnico SIFEN v150
    Schema Download: http://ekuatia.set.gov.py/sifen/xsd
    Portal: https://ekuatia.set.gov.py
    Test Environment: Available for development

Last Updated: Based on Manual Técnico SIFEN v150 - September 2019
