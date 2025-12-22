#!/usr/bin/env python3
"""
Migrate Farmer Registration Forms from jdx1 to jdx4

Source: jdx1/farmlandRegistry - 11 forms starting with "01"
Target: jdx4/farmersPortal

This script:
1. Extracts form definitions from jdx1 database
2. Inserts them into jdx4 database
3. Creates a single CRUD menu item for farmerRegistrationForm in userview "v"
"""

import json
import os
import mysql.connector
from datetime import datetime

# Form IDs to migrate (names starting with "01")
FORMS_TO_MIGRATE = [
    'farmerRegistrationForm',  # 01 - Farmer Registration Form (main form)
    'farmerBasicInfo',         # 01.01 - Farmer Basic Information
    'farmerLocation',          # 01.02 - Farmer Location and Farm
    'farmerAgriculture',       # 01.03 - Farmer Agricultural Activities
    'farmerHousehold',         # 01.04 - Farmer Household Members
    'householdMemberForm',     # 01.04-1 - Household Member Form
    'farmerCropsLivestock',    # 01.05 - Farmer Crops and Livestock
    'cropManagementForm',      # 01.05-1 - Crop Management Form
    'livestockDetailsForm',    # 01.05-2 - Livestock Details Form
    'farmerIncomePrograms',    # 01.06 - Farmer Income and Programs
    'farmerDeclaration',       # 01.07 - Farmer Declaration
]

SOURCE_APP_ID = 'farmlandRegistry'
TARGET_APP_ID = 'farmersPortal'
TARGET_APP_VERSION = 1
USERVIEW_ID = 'v'
CATEGORY_LABEL = 'Farmer Application'


def get_source_connection():
    """Connect to jdx1 database (mysql1 port 3306)"""
    return mysql.connector.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password=os.environ.get('MYSQL1_ROOT_PASSWORD', ''),
        database='jwdb'
    )


def get_target_connection():
    """Connect to jdx4 database (mysql4 port 3309)"""
    return mysql.connector.connect(
        host='127.0.0.1',
        port=3309,
        user='root',
        password=os.environ.get('MYSQL4_ROOT_PASSWORD', ''),
        database='jwdb'
    )


def extract_forms(source_conn, form_ids: list[str]) -> list[dict]:
    """Extract form definitions from source database"""
    cursor = source_conn.cursor(dictionary=True)

    placeholders = ', '.join(['%s'] * len(form_ids))
    query = f"""
        SELECT formId, name, tableName, json, description, dateCreated, dateModified
        FROM app_form
        WHERE appId = %s AND formId IN ({placeholders})
    """

    cursor.execute(query, [SOURCE_APP_ID] + form_ids)
    forms = cursor.fetchall()
    cursor.close()

    return forms


def check_existing_forms(target_conn, form_ids: list[str]) -> list[str]:
    """Check which forms already exist in target"""
    cursor = target_conn.cursor()

    placeholders = ', '.join(['%s'] * len(form_ids))
    query = f"""
        SELECT formId FROM app_form
        WHERE appId = %s AND formId IN ({placeholders})
    """

    cursor.execute(query, [TARGET_APP_ID] + form_ids)
    existing = [row[0] for row in cursor.fetchall()]
    cursor.close()

    return existing


def insert_forms(target_conn, forms: list[dict], skip_existing: list[str]):
    """Insert forms into target database"""
    cursor = target_conn.cursor()

    insert_query = """
        INSERT INTO app_form (appId, appVersion, formId, name, tableName, json, description, dateCreated, dateModified)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    inserted = []
    skipped = []

    for form in forms:
        if form['formId'] in skip_existing:
            skipped.append(form['formId'])
            continue

        now = datetime.now()
        cursor.execute(insert_query, (
            TARGET_APP_ID,
            TARGET_APP_VERSION,
            form['formId'],
            form['name'],
            form['tableName'],
            form['json'],
            form['description'],
            now,
            now
        ))
        inserted.append(form['formId'])

    target_conn.commit()
    cursor.close()

    return inserted, skipped


def get_userview_json(target_conn, userview_id: str) -> dict | None:
    """Get userview JSON from target database"""
    cursor = target_conn.cursor()

    query = """
        SELECT json FROM app_userview
        WHERE appId = %s AND id = %s
    """

    cursor.execute(query, [TARGET_APP_ID, userview_id])
    row = cursor.fetchone()
    cursor.close()

    if row and row[0]:
        try:
            return json.loads(row[0])
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse userview JSON: {e}")
            return None
    return None


def update_userview_json(target_conn, userview_id: str, userview_json: dict):
    """Update userview JSON in target database"""
    cursor = target_conn.cursor()

    query = """
        UPDATE app_userview
        SET json = %s, dateModified = %s
        WHERE appId = %s AND id = %s
    """

    cursor.execute(query, [
        json.dumps(userview_json),
        datetime.now(),
        TARGET_APP_ID,
        userview_id
    ])

    target_conn.commit()
    cursor.close()


def find_or_create_category(userview_json: dict, category_label: str) -> dict:
    """Find existing category or create new one"""
    categories = userview_json.get('categories', [])

    # Look for existing category
    for cat in categories:
        props = cat.get('properties', {})
        if props.get('label') == category_label:
            return cat

    # Create new category
    import uuid
    new_category = {
        "className": "org.joget.apps.userview.model.UserviewCategory",
        "menus": [],
        "properties": {
            "id": f"category-{uuid.uuid4().hex.upper()[:32]}",
            "label": category_label
        }
    }

    categories.append(new_category)
    userview_json['categories'] = categories

    return new_category


def create_crud_menu(form_id: str, form_name: str) -> dict:
    """Create a CRUD menu item for the form"""
    import uuid

    return {
        "className": "org.joget.apps.userview.lib.FormMenu",
        "properties": {
            "id": uuid.uuid4().hex.upper()[:32],
            "label": form_name,
            "formId": form_id,
            "pageSize": "10",
            "buttonPosition": "bottomLeft",
            "keyName": "id"
        }
    }


def add_menu_to_category(category: dict, menu: dict) -> bool:
    """Add menu to category if not already present"""
    menus = category.get('menus', [])

    # Check if menu with same formId already exists
    for existing_menu in menus:
        if existing_menu.get('properties', {}).get('formId') == menu['properties']['formId']:
            return False

    menus.append(menu)
    category['menus'] = menus
    return True


def main():
    print("=" * 60)
    print("Farmer Registration Forms Migration")
    print("=" * 60)
    print(f"Source: jdx1/{SOURCE_APP_ID}")
    print(f"Target: jdx4/{TARGET_APP_ID}")
    print(f"Forms to migrate: {len(FORMS_TO_MIGRATE)}")
    print()

    # Connect to databases
    print("Connecting to databases...")
    source_conn = get_source_connection()
    target_conn = get_target_connection()
    print("  Connected to jdx1 (mysql1:3306)")
    print("  Connected to jdx4 (mysql4:3309)")
    print()

    # Extract forms from source
    print("Extracting forms from source...")
    forms = extract_forms(source_conn, FORMS_TO_MIGRATE)
    print(f"  Found {len(forms)} forms in source")

    if len(forms) != len(FORMS_TO_MIGRATE):
        missing = set(FORMS_TO_MIGRATE) - {f['formId'] for f in forms}
        print(f"  Warning: Missing forms: {missing}")
    print()

    # Check existing forms in target
    print("Checking existing forms in target...")
    existing = check_existing_forms(target_conn, FORMS_TO_MIGRATE)
    if existing:
        print(f"  Found {len(existing)} existing forms (will skip): {existing}")
    else:
        print("  No existing forms found")
    print()

    # Insert forms
    print("Inserting forms into target...")
    inserted, skipped = insert_forms(target_conn, forms, existing)
    print(f"  Inserted: {len(inserted)} forms")
    for form_id in inserted:
        form = next((f for f in forms if f['formId'] == form_id), None)
        if form:
            print(f"    - {form_id}: {form['name']}")

    if skipped:
        print(f"  Skipped (already exist): {len(skipped)} forms")
        for form_id in skipped:
            print(f"    - {form_id}")
    print()

    # Add menu item for farmerRegistrationForm
    print("Adding menu item for farmerRegistrationForm...")

    userview_json = get_userview_json(target_conn, USERVIEW_ID)
    if not userview_json:
        print("  Error: Could not load userview JSON")
        print("  Skipping menu creation")
    else:
        # Find or create category
        category = find_or_create_category(userview_json, CATEGORY_LABEL)
        print(f"  Using category: {CATEGORY_LABEL}")

        # Get form name for the menu
        main_form = next((f for f in forms if f['formId'] == 'farmerRegistrationForm'), None)
        form_name = main_form['name'] if main_form else '01 - Farmer Registration Form'

        # Create and add menu
        menu = create_crud_menu('farmerRegistrationForm', form_name)

        if add_menu_to_category(category, menu):
            update_userview_json(target_conn, USERVIEW_ID, userview_json)
            print(f"  Added menu: {form_name}")
        else:
            print("  Menu already exists, skipping")

    print()

    # Cleanup
    source_conn.close()
    target_conn.close()

    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print()
    print("IMPORTANT: Restart Tomcat on jdx4 to clear Joget cache:")
    print("  cd ~/joget-enterprise-linux-9.0.3 && ./tomcat.sh restart")


if __name__ == '__main__':
    main()
