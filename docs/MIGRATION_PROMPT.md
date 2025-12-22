# Instance Migration Prompt Template

Use this template when requesting migration of components between Joget instances.

---

## Migration Request Template

```
I need to migrate [component type] from [source instance] to [target instance].

**Source:**
- Instance: [jdx1/jdx2/jdx3/jdx4/jdx5/jdx6]
- Application: [app_id]
- Pattern: [form pattern, e.g., "md%" for all MDM forms, or specific form ID]

**Target:**
- Instance: [jdx1/jdx2/jdx3/jdx4/jdx5/jdx6]
- Application: [app_id]

**Options:**
- [ ] Include data (copy table contents)
- [ ] Add menu items to userview
  - Userview ID: [e.g., "v"]
  - Category label: [e.g., "Master Data"]

**Pre-migration checklist:**
- [ ] Target category already exists in userview (if adding menus)
- [ ] Source instance is running
- [ ] Target instance is running
```

---

## Example Requests

### Example 1: Migrate MDM Forms with Data and Menus

```
I need to migrate MDM forms from jdx3 to jdx4.

**Source:**
- Instance: jdx3
- Application: subsidyApplication
- Pattern: md%

**Target:**
- Instance: jdx4
- Application: farmersPortal

**Options:**
- [x] Include data (copy table contents)
- [x] Add menu items to userview
  - Userview ID: v
  - Category label: Master Data

**Pre-migration checklist:**
- [x] Target category already exists in userview
- [x] Source instance is running
- [x] Target instance is running
```

### Example 2: Migrate Specific Forms Only (No Data)

```
I need to migrate equipment forms from jdx3 to jdx4.

**Source:**
- Instance: jdx3
- Application: subsidyApplication
- Pattern: eq%

**Target:**
- Instance: jdx4
- Application: farmersPortal

**Options:**
- [ ] Include data (copy table contents)
- [ ] Add menu items to userview

**Pre-migration checklist:**
- [x] Source instance is running
- [x] Target instance is running
```

### Example 3: Migrate All Forms from One App to Another

```
I need to migrate all forms from jdx3 to jdx5.

**Source:**
- Instance: jdx3
- Application: subsidyApplication
- Pattern: (all forms)

**Target:**
- Instance: jdx5
- Application: farmersPortal

**Options:**
- [x] Include data (copy table contents)
- [ ] Add menu items to userview

**Pre-migration checklist:**
- [x] Source instance is running
- [x] Target instance is running
```

---

## CLI Command Reference

### Dry-Run (Preview Only)

```bash
joget-deploy migrate \
  --source jdx3 \
  --source-app subsidyApplication \
  --target jdx4 \
  --target-app farmersPortal \
  --pattern "md%" \
  --dry-run
```

### Full Migration with Data

```bash
joget-deploy migrate \
  --source jdx3 \
  --source-app subsidyApplication \
  --target jdx4 \
  --target-app farmersPortal \
  --pattern "md%" \
  --with-data
```

### Full Migration with Data and Menus

```bash
joget-deploy migrate \
  --source jdx3 \
  --source-app subsidyApplication \
  --target jdx4 \
  --target-app farmersPortal \
  --pattern "md%" \
  --with-data \
  --userview v \
  --category "Master Data"
```

### Overwrite Existing (Instead of Skip)

```bash
joget-deploy migrate \
  --source jdx3 \
  --source-app subsidyApplication \
  --target jdx4 \
  --target-app farmersPortal \
  --pattern "md%" \
  --with-data \
  --overwrite
```

---

## Python API Reference

```python
from joget_deployment_toolkit import JogetClient, InstanceMigrator

# Connect to instances
source = JogetClient.from_instance('jdx3')
target = JogetClient.from_instance('jdx4')

# Create migrator
migrator = InstanceMigrator(source, target)

# Analyze first (recommended)
analysis = migrator.analyze(
    source_app_id='subsidyApplication',
    target_app_id='farmersPortal',
    pattern='md%',
    userview_id='v',
    category_label='Master Data'
)
print(analysis)

# Execute migration
result = migrator.migrate_app_component(
    source_app_id='subsidyApplication',
    target_app_id='farmersPortal',
    pattern='md%',
    with_data=True,
    userview_id='v',
    category_label='Master Data'
)

# Check results
if result.success:
    print(f"✓ Migrated {result.forms_migrated} forms")
    print(f"✓ Migrated {result.datalists_migrated} datalists")
    print(f"✓ Copied {result.data_records_copied} data records")
    print(f"✓ Added {result.menus_added} menu items")
else:
    print("Migration had errors:")
    for error in result.errors:
        print(f"  - {error}")
```

---

## Important Notes

### Before Migration

1. **Create target category first** - If adding menu items, the category must already exist in the target userview. Create it manually in Joget UI before running migration.

2. **Check instance status** - Ensure both source and target instances are running:
   ```bash
   joget-deploy status
   ```

3. **Set environment variables** - Ensure passwords are available:
   ```bash
   source /Users/aarelaponin/PycharmProjects/dev/joget-instance-manager/.env
   ```

### After Migration

1. **Restart Tomcat** - Joget caches userview definitions. Changes won't be visible until Tomcat is restarted on the target instance.

2. **Verify in UI** - Access the target userview to confirm menus appear correctly:
   ```
   http://localhost:808X/jw/web/userview/{app_id}/{userview_id}
   ```

### Migration Order

The migrator handles dependencies automatically in this order:
1. Forms (no dependencies)
2. Data tables (depend on forms)
3. Datalists (reference forms)
4. Userview menus (reference datalists + forms)

### What Gets Migrated

| Component | Table | Pattern Example |
|-----------|-------|-----------------|
| Forms | `app_form` | `md%` → md01, md02, ... md47 |
| Datalists | `app_datalist` | `list_md%` → list_md01, list_md02, ... |
| Data | `app_fd_{table}` | All rows from matching tables |
| Menus | `app_userview` (JSON) | CrudMenu items added to category |

### What Does NOT Get Migrated

- Userview structure (categories, layout) - must be created manually
- Process definitions
- Plugins
- Custom themes
- Environment variables
