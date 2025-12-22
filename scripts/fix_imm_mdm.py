#!/usr/bin/env python3
"""
IMM MDM Fix Script

1. Fixes data columns (copies from non-prefixed to c_* prefixed columns)
2. Renames IMM category to "Master Data" and consolidates all MDM menus
"""

import json
import sys
from datetime import datetime

import mysql.connector

# Configuration
TARGET_APP_ID = "subsidyApplication"
TARGET_APP_VERSION = 1
USERVIEW_ID = "v"

# Database configuration (jdx3 / mysql3)
DB_CONFIG = {
    "host": "localhost",
    "port": 3308,
    "user": "root",
    "password": "at456vkm",
    "database": "jwdb",
    "unix_socket": "/tmp/mysql3.sock"
}

# MDM form tables to fix
MDM_TABLES = [
    "app_fd_md38InputCategory",
    "app_fd_md39CampaignType",
    "app_fd_md40DistribModel",
    "app_fd_md41AllocBasis",
    "app_fd_md42TargetCategory",
    "app_fd_md43DealerCategory",
    "app_fd_md44Input",
    "app_fd_md45DistribPoint",
    "app_fd_md46InputPackage",
]

# Fields to copy (source -> c_source)
COMMON_FIELDS = ["code", "name", "description", "sortOrder", "isActive"]


def get_table_columns(cursor, table_name: str) -> list[str]:
    """Get all column names for a table."""
    cursor.execute(f"DESCRIBE `{table_name}`")
    return [row[0] for row in cursor.fetchall()]


def fix_data_columns(cursor, table_name: str) -> int:
    """Copy data from non-prefixed columns to c_* prefixed columns."""
    columns = get_table_columns(cursor, table_name)

    # Find pairs of columns (col and c_col)
    updates = []
    for col in columns:
        if not col.startswith("c_") and f"c_{col}" in columns:
            updates.append((col, f"c_{col}"))

    if not updates:
        return 0

    # Build UPDATE statement
    set_clauses = [f"`{c_col}` = `{col}`" for col, c_col in updates]
    sql = f"UPDATE `{table_name}` SET {', '.join(set_clauses)} WHERE `{updates[0][1]}` IS NULL OR `{updates[0][1]}` = ''"

    cursor.execute(sql)
    return cursor.rowcount


def get_userview_json(cursor, app_id: str, userview_id: str, app_version: int) -> dict | None:
    """Get the userview JSON definition."""
    cursor.execute(
        "SELECT json FROM app_userview WHERE appId = %s AND appVersion = %s AND id = %s",
        (app_id, app_version, userview_id)
    )
    result = cursor.fetchone()
    if result and result[0]:
        return json.loads(result[0])
    return None


def update_userview_json(cursor, app_id: str, userview_id: str, app_version: int,
                         userview_json: dict):
    """Update the userview JSON definition."""
    now = datetime.now()
    cursor.execute(
        "UPDATE app_userview SET json = %s, dateModified = %s WHERE appId = %s AND appVersion = %s AND id = %s",
        (json.dumps(userview_json), now, app_id, app_version, userview_id)
    )


def consolidate_mdm_menus(userview_json: dict) -> tuple[int, int]:
    """
    Consolidate all MDM menus under a single "Master Data" category.
    Returns (menus_moved, categories_removed).
    """
    categories = userview_json.get("categories", [])

    # Find or create Master Data category
    master_data_category = None
    master_data_idx = None

    for idx, category in enumerate(categories):
        props = category.get("properties", {})
        label = props.get("label", "")
        if "IMM Master Data" in label or "Master Data" in label:
            master_data_category = category
            master_data_idx = idx
            break

    if not master_data_category:
        # Create new Master Data category
        master_data_category = {
            "className": "org.joget.apps.userview.model.UserviewCategory",
            "menus": [],
            "properties": {
                "id": "category-master-data",
                "label": '<i class="fa fa-database"></i> Master Data',
                "hide": "",
                "permission": {"className": "", "properties": {}},
            }
        }
        categories.append(master_data_category)
        master_data_idx = len(categories) - 1
    else:
        # Rename existing IMM category to Master Data
        master_data_category["properties"]["label"] = '<i class="fa fa-database"></i> Master Data'

    # Collect all MDM menus from other categories
    menus_moved = 0
    categories_to_remove = []

    for idx, category in enumerate(categories):
        if idx == master_data_idx:
            continue

        props = category.get("properties", {})
        label = props.get("label", "")

        # Check if this is an MDM-related category
        is_mdm_category = any(keyword in label.lower() for keyword in
                             ["master data", "mdm", "md.", "lookup", "reference"])

        menus = category.get("menus", [])
        mdm_menus_in_category = []
        non_mdm_menus = []

        for menu in menus:
            menu_props = menu.get("properties", {})
            menu_label = menu_props.get("label", "")
            datalist_id = menu_props.get("datalistId", "")
            form_id = menu_props.get("editFormId", "") or menu_props.get("addFormId", "")
            custom_id = menu_props.get("customId", "")

            # Check if this menu is MDM-related
            is_mdm_menu = (
                menu_label.startswith("MD.") or
                datalist_id.startswith("list_md") or
                form_id.startswith("md") or
                custom_id.startswith("crud_md") or
                "master" in menu_label.lower()
            )

            if is_mdm_menu:
                mdm_menus_in_category.append(menu)
            else:
                non_mdm_menus.append(menu)

        # Move MDM menus to Master Data category
        if mdm_menus_in_category:
            # Check for duplicates before adding
            existing_datalists = {m.get("properties", {}).get("datalistId")
                                 for m in master_data_category.get("menus", [])}

            for menu in mdm_menus_in_category:
                menu_datalist = menu.get("properties", {}).get("datalistId")
                if menu_datalist not in existing_datalists:
                    master_data_category.setdefault("menus", []).append(menu)
                    existing_datalists.add(menu_datalist)
                    menus_moved += 1

            # Update category with remaining menus
            category["menus"] = non_mdm_menus

        # Mark empty categories or MDM-only categories for removal
        if is_mdm_category and not non_mdm_menus:
            categories_to_remove.append(idx)

    # Remove empty MDM categories (in reverse order to preserve indices)
    for idx in sorted(categories_to_remove, reverse=True):
        if idx != master_data_idx:
            del categories[idx]

    userview_json["categories"] = categories

    return menus_moved, len(categories_to_remove)


def main(dry_run: bool = False):
    """Main fix function."""
    print("=" * 60)
    print("IMM MDM Fix Script")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE FIX'}")
    print("=" * 60)

    # Connect to database
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print(f"\n✓ Connected to database: {DB_CONFIG['database']}")
    except mysql.connector.Error as e:
        print(f"ERROR: Database connection failed: {e}")
        return 1

    # PART 1: Fix data columns
    print("\n" + "=" * 40)
    print("PART 1: Fix Data Columns")
    print("=" * 40)

    total_rows_fixed = 0

    for table_name in MDM_TABLES:
        # Check if table exists
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (DB_CONFIG["database"], table_name)
        )
        if cursor.fetchone()[0] == 0:
            print(f"  {table_name}: table doesn't exist - skip")
            continue

        if dry_run:
            # Count rows that would be fixed
            columns = get_table_columns(cursor, table_name)
            c_cols = [c for c in columns if c.startswith("c_") and c[2:] in columns]
            if c_cols:
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}` WHERE `{c_cols[0]}` IS NULL OR `{c_cols[0]}` = ''")
                count = cursor.fetchone()[0]
                print(f"  {table_name}: would fix {count} rows")
            else:
                print(f"  {table_name}: no c_* columns to fix")
        else:
            rows_fixed = fix_data_columns(cursor, table_name)
            print(f"  ✓ {table_name}: fixed {rows_fixed} rows")
            total_rows_fixed += rows_fixed

    # PART 2: Consolidate MDM menus
    print("\n" + "=" * 40)
    print("PART 2: Consolidate Master Data Menus")
    print("=" * 40)

    userview_json = get_userview_json(cursor, TARGET_APP_ID, USERVIEW_ID, TARGET_APP_VERSION)
    if not userview_json:
        print("ERROR: Userview not found")
        return 1

    if dry_run:
        # Make a copy for dry run
        import copy
        test_json = copy.deepcopy(userview_json)
        menus_moved, cats_removed = consolidate_mdm_menus(test_json)
        print(f"  Would move {menus_moved} menus")
        print(f"  Would remove {cats_removed} empty categories")
        print(f"  Would rename category to 'Master Data'")
    else:
        menus_moved, cats_removed = consolidate_mdm_menus(userview_json)
        print(f"  ✓ Moved {menus_moved} menus to Master Data")
        print(f"  ✓ Removed {cats_removed} empty categories")
        print(f"  ✓ Renamed category to 'Master Data'")

        # Update userview
        update_userview_json(cursor, TARGET_APP_ID, USERVIEW_ID, TARGET_APP_VERSION, userview_json)
        print(f"  ✓ Userview updated")

    # Commit changes
    if not dry_run:
        conn.commit()
        print("\n✓ All changes committed")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if not dry_run:
        print(f"Data rows fixed: {total_rows_fixed}")
        print(f"Menus consolidated: {menus_moved}")
        print(f"\n⚠ RESTART JOGET to see UI changes")

    cursor.close()
    conn.close()

    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python fix_imm_mdm.py [--dry-run|-n]")
        print("\nFixes:")
        print("  1. Copies data from non-prefixed columns to c_* columns")
        print("  2. Renames IMM category to 'Master Data'")
        print("  3. Consolidates all MDM menus under Master Data")
        sys.exit(0)

    sys.exit(main(dry_run=dry_run))
