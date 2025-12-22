# Module Deployment Prompt Template

Use this template when asking Claude to deploy a new module to Joget.

---

## Quick Version (Copy & Customize)

```
Deploy the [MODULE_NAME] module.

Location: components/[MODULE_NAME]/
Target: [INSTANCE] / [APP_ID]
Mode: [full | forms-only | mdm-only | validate]

Notes: [Any special considerations]
```

**Example:**
```
Deploy the IMM module.

Location: components/imm/
Target: jdx3 / farmersPortal
Mode: full

Notes: This is a new module, deploy MDM first then main forms.
```

---

## Detailed Version (For Complex Deployments)

```
## Module Deployment Request

### Module Information
- **Name**: [MODULE_NAME]
- **Description**: [Brief description of what this module does]
- **Location**: components/[MODULE_NAME]/

### Module Structure
- Forms: components/[MODULE_NAME]/forms/
- MDM Forms: components/[MODULE_NAME]/mdm/forms/
- MDM Data: components/[MODULE_NAME]/mdm/data/

### Target Environment
- **Instance**: [jdx3 | jdx4 | jdx5 | ...]
- **Application ID**: [e.g., farmersPortal]
- **Application Version**: [1]

### Deployment Mode
Select one:
- [ ] Full deployment (MDM + forms)
- [ ] Forms only (skip MDM)
- [ ] MDM only (forms already exist)
- [ ] Validation only (no deployment)

### Deployment Options
- [ ] Dry-run first (preview changes)
- [ ] Verbose output
- [ ] Auto-confirm (skip prompts)

### Dependencies
External forms this module requires:
- [List any MDM forms or other forms that must exist]

### Special Instructions
[Any specific requirements, order constraints, or known issues]

### Post-Deployment
- [ ] Verify forms in Joget console
- [ ] Test form functionality
- [ ] Check data loaded correctly
```

---

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| Module Name | Yes | Short identifier (e.g., imm, crm, inventory) |
| Location | Yes | Path under `components/` directory |
| Instance | Yes | Target Joget instance name from `~/.joget/instances.yaml` |
| Application ID | Yes | Target application in Joget |
| Mode | Yes | What to deploy: full, forms-only, mdm-only, validate |
| Dependencies | Recommended | External forms the module references |
| Special Instructions | Optional | Any constraints or requirements |

---

## Deployment Modes Explained

### Full Deployment
Deploys everything in order:
1. MDM forms (`mdm/forms/*.json`)
2. MDM data (`mdm/data/*.csv`)
3. Main forms (`forms/*.json`)

Best for: New modules, fresh installations

### Forms Only
Deploys only main forms:
1. Main forms (`forms/*.json`)

Best for: MDM already exists, updating forms only

### MDM Only
Deploys MDM components:
1. MDM forms (`mdm/forms/*.json`)
2. MDM data (`mdm/data/*.csv`)

Best for: Setting up reference data before main forms

### Validation Only
Checks without deploying:
1. JSON syntax validation
2. Form ID length check
3. Dependency analysis
4. Deployment order preview

Best for: Pre-flight check, CI/CD pipelines

---

## Example Prompts

### Example 1: New Module Full Deployment
```
Deploy the IMM (Input Management Module).

Location: components/imm/
Target: jdx3 / farmersPortal
Mode: full

This is a new module for managing agricultural input distribution campaigns.
Please validate first, then deploy MDM, then main forms.
```

### Example 2: Update Existing Forms
```
Deploy updated forms for the IMM module.

Location: components/imm/forms/
Target: jdx3 / farmersPortal
Mode: forms-only

Only the main forms have changed. MDM is already deployed.
Use dry-run first to see what will be overwritten.
```

### Example 3: Validation Only
```
Validate the IMM module package.

Location: components/imm/
Target: jdx3 / farmersPortal
Mode: validate

Check all JSON files, dependencies, and show deployment order.
Do not deploy anything.
```

### Example 4: Multi-Instance Deployment
```
Deploy the IMM module to multiple instances.

Location: components/imm/
Targets:
  1. jdx3 / farmersPortal (dev)
  2. jdx4 / farmersPortal (staging)
Mode: full

Deploy to dev first, verify, then deploy to staging.
```

---

## What Claude Will Do

When you provide a deployment request, Claude will:

1. **Explore the module structure**
   - List all forms in the module
   - Identify MDM vs main forms
   - Check for data files

2. **Validate the package**
   - Run `joget-deploy check` on the forms
   - Report any JSON errors
   - Identify external dependencies

3. **Analyze dependencies**
   - Show internal dependencies
   - List external dependencies (MDM forms, etc.)
   - Calculate deployment order

4. **Execute deployment** (with your confirmation)
   - Connect to target instance
   - Deploy in correct order
   - Report results

5. **Provide verification**
   - Show deployment summary
   - Provide console URL for verification
   - List any failures

---

## Tips for Best Results

1. **Always validate first** - Ask for validation before actual deployment
2. **Use dry-run** - Preview changes before committing
3. **Specify dependencies** - List what MDM forms the module needs
4. **One instance at a time** - Deploy to dev, verify, then staging
5. **Check instance status** - Run `joget-deploy status` first
6. **Be explicit about mode** - Say "full", "forms-only", etc.

---

## Slash Command Usage

You can also use the slash command:
```
/deploy-module imm
```

This will load a template with the module name pre-filled.
