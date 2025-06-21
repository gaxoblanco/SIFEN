# 🚀 Quick Commit Template

## **Structure**
```
<type>(scope): <description>

✅ X tests passing for <file>.xsd
✅ <Main validation> per SIFEN spec  
✅ <Key feature> working
✅ <Technical detail>
✅ Schema/Performance/Compliance note

Files: <main_file>.py, <schema>.xsd
Coverage: <What's complete>
```

## **Quick Reference**

**Types:** `feat` `fix` `test` `refactor` `docs`

**Scopes:** `schemas.v150` `tests` `xml` `validation` `api`

**Common achievements:**
- `✅ XX tests passing for <module>.xsd`
- `✅ <Validation> per SIFEN spec`
- `✅ Schema XSD modular structure working`
- `✅ Full namespace compliance`
- `✅ Error handling & debugging`
- `✅ Performance tests under XXXms`

**SIFEN specifics:**
- Paraguay departments (1-17)
- Document types: FE(1), AFE(4), NCE(5), NDE(6), NRE(7)
- Error codes: E948, E949, D216, D322
- Always mention "per SIFEN spec" or "per Paraguay standards"

## **Example**
```bash
feat(schemas.v150): Complete geographic types tests & hierarchical validation

✅ 23 tests passing for geographic_types.xsd
✅ Department codes validation (1-99) per Paraguay geography
✅ Hierarchical validation Department→District→City
✅ SIFEN error codes E948/E949 validation
✅ Schema path resolution & debugging utilities

Files: test_geographic_types.py, geographic_types.xsd
Coverage: Complete SIFEN v150 geographic validation system
```