# IMM Module Deployment Request

## Module Information
- **Name**: IMM (Inputs Management Module)
- **Description**: Agricultural input distribution management - campaigns, entitlements, distribution transactions, and agro-dealer management
- **Location**: `/Users/aarelaponin/PycharmProjects/dev/joget-form-generator/specs/imm/output/`

## Module Structure

This module contains **18 forms** in a flat directory (all JSON files):

### Master Data Forms (10 forms)
| Form ID | Name | Dependencies |
|---------|------|--------------|
| md38InputCategory | Input Category | (none) |
| md39CampaignType | Campaign Type | (none) |
| md40DistribModel | Distribution Model | (none) |
| md41AllocBasis | Allocation Basis | (none) |
| md42TargetCategory | Target Farmer Category | (none) |
| md43DealerCategory | Dealer Category | (none) |
| md44Input | Input Catalogue | md38InputCategory |
| md45DistribPoint | Distribution Point | mdDistrict (external), imAgroDealer |
| md46InputPackage | Input Package | md42TargetCategory, md47PackageContent |
| md47PackageContent | Package Content (grid) | md44Input |

### Grid Sub-forms (4 forms)
| Form ID | Name | Used By |
|---------|------|---------|
| imCampaignInput | Campaign Input | imCampaign |
| imCampaignDistPt | Campaign Distribution Point | imCampaign |
| imEntitlementItem | Entitlement Item | imEntitlement |
| imDistribItem | Distribution Item | imDistribution |

### Main Transactional Forms (4 forms)
| Form ID | Name | Dependencies |
|---------|------|--------------|
| imAgroDealer | Agro-Dealer Registration | md43DealerCategory, mdDistrict (external) |
| imCampaign | Campaign Management | md39CampaignType, md40DistribModel, mdDistrict (external), mdAgroEcoZone (external), md42TargetCategory, imCampaignInput, imCampaignDistPt |
| imEntitlement | Farmer Entitlement | imCampaign, farmerBasicInfo (external), imEntitlementItem |
| imDistribution | Distribution Transaction | imEntitlement, md45DistribPoint, imDistribItem |

## Target Environment
- **Instance**: jdx-imm (or configure for localhost:8888)
- **URL**: http://localhost:8888/jw
- **Database Port**: 3308
- **Application ID**: farmersPortal
- **Application Version**: 1

## External Dependencies
These forms must already exist in the target application:
- `mdDistrict` - Districts of Lesotho
- `mdAgroEcoZone` - Agro-ecological zones
- `farmerBasicInfo` - Farmer registration (for entitlement lookup)

## Deployment Mode
- [x] Full deployment (all 18 forms)
- [ ] Forms only
- [ ] Validation only

## Deployment Options
- [x] Dry-run first (preview changes)
- [x] Verbose output
- [ ] Auto-confirm (I want to review before deploying)

## Deployment Order
Deploy in this exact order (dependencies first):

**Phase 1: Simple Master Data** (no internal dependencies)
1. md38InputCategory
2. md39CampaignType
3. md40DistribModel
4. md41AllocBasis
5. md42TargetCategory
6. md43DealerCategory

**Phase 2: Master Data with Dependencies**
7. md44Input (depends on md38InputCategory)
8. md47PackageContent (depends on md44Input)
9. imAgroDealer (depends on md43DealerCategory) - needed by md45DistribPoint
10. md45DistribPoint (depends on mdDistrict, imAgroDealer)
11. md46InputPackage (depends on md42TargetCategory, md47PackageContent)

**Phase 3: Grid Sub-forms**
12. imCampaignInput (depends on md44Input, md41AllocBasis)
13. imCampaignDistPt (depends on md45DistribPoint)
14. imEntitlementItem (depends on md44Input)
15. imDistribItem (depends on md44Input)

**Phase 4: Main Transactional Forms**
16. imCampaign (depends on multiple MDM + grids)
17. imEntitlement (depends on imCampaign + grid)
18. imDistribution (depends on imEntitlement + grid)

## Special Instructions
1. **Verify external dependencies first** - Check that mdDistrict, mdAgroEcoZone, and farmerBasicInfo exist in farmersPortal before starting
2. **This is first deployment** - All 18 forms are new, none exist in target app yet
3. **Grid forms must deploy before parent forms** - imCampaignInput before imCampaign, etc.
4. **imAgroDealer before md45DistribPoint** - DistribPoint has optional lookup to AgroDealer

## Pre-Deployment Checklist
- [ ] Instance jdx-imm is running (http://localhost:8888/jw accessible)
- [ ] Application farmersPortal exists
- [ ] External dependencies exist (mdDistrict, mdAgroEcoZone)
- [ ] All 18 JSON files present in output directory

## Post-Deployment Verification
- [ ] All 18 forms visible in Joget console
- [ ] Master data forms can be opened without errors
- [ ] Grid forms load correctly in parent forms
- [ ] Lookup dropdowns populate correctly (e.g., districts, input categories)
- [ ] Campaign form can create new campaign record

## Verification URL
After deployment, verify at:
```
http://localhost:8888/jw/web/console/app/farmersPortal/1/forms
```

---

## Quick Command
```
Deploy the IMM module.

Location: /Users/aarelaponin/PycharmProjects/dev/joget-form-generator/specs/imm/output/
Target: localhost:8888 / farmersPortal
Mode: full

Notes: 
- 18 forms total (10 MDM, 4 grids, 4 transactional)
- External dependencies: mdDistrict, mdAgroEcoZone, farmerBasicInfo
- First deployment - all forms are new
- Dry-run first to validate
```
