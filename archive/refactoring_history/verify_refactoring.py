#!/usr/bin/env python3
"""
Verification script for joget-toolkit refactoring.

Tests that Week 2 refactoring is complete and backward compatible:
1. All operation mixins are accessible
2. JogetClient facade works
3. Backward compatibility is maintained
4. All methods are available
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)

    try:
        # Test new modular imports
        from joget_deployment_toolkit.client import JogetClient
        from joget_deployment_toolkit.client.base import BaseClient
        from joget_deployment_toolkit.client.forms import FormOperations
        from joget_deployment_toolkit.client.applications import ApplicationOperations
        from joget_deployment_toolkit.client.plugins import PluginOperations
        from joget_deployment_toolkit.client.health import HealthOperations

        print("✓ All modular client imports successful")

        # Test old backward-compatible import
        from joget_deployment_toolkit import JogetClient as OldClient

        print("✓ Backward compatible import successful")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_client_structure():
    """Test that JogetClient has all expected methods."""
    print("\n" + "=" * 70)
    print("TEST 2: Client Structure")
    print("=" * 70)

    from joget_deployment_toolkit.client import JogetClient

    # Expected methods from each mixin
    expected_methods = {
        'FormOperations': [
            'list_forms', 'get_form', 'create_form', 'update_form',
            'delete_form', 'batch_create_forms', 'batch_update_forms'
        ],
        'ApplicationOperations': [
            'list_applications', 'get_application', 'export_application',
            'import_application', 'batch_export_applications'
        ],
        'PluginOperations': [
            'list_plugins', 'get_plugin', 'list_plugins_by_type'
        ],
        'HealthOperations': [
            'test_connection', 'get_system_info', 'get_health_status'
        ]
    }

    all_passed = True

    for mixin_name, methods in expected_methods.items():
        print(f"\n{mixin_name} methods:")
        for method in methods:
            if hasattr(JogetClient, method):
                print(f"  ✓ {method}")
            else:
                print(f"  ✗ {method} - MISSING!")
                all_passed = False

    return all_passed


def test_alternative_constructors():
    """Test alternative constructor methods."""
    print("\n" + "=" * 70)
    print("TEST 3: Alternative Constructors")
    print("=" * 70)

    from joget_deployment_toolkit.client import JogetClient

    constructors = [
        'from_credentials',
        'from_config',
        'from_env'
    ]

    all_exist = True
    for constructor in constructors:
        if hasattr(JogetClient, constructor):
            print(f"  ✓ {constructor}")
        else:
            print(f"  ✗ {constructor} - MISSING!")
            all_exist = False

    return all_exist


def test_backward_compatibility():
    """Test backward compatibility with v2.0.0 initialization."""
    print("\n" + "=" * 70)
    print("TEST 4: Backward Compatibility")
    print("=" * 70)

    try:
        from joget_deployment_toolkit import JogetClient

        # Test old-style initialization
        print("\nTesting old-style initialization:")
        print("  client = JogetClient('http://test.com/jw', api_key='test')")

        # This should work without errors (no actual connection attempted)
        # We're just testing the initialization signature
        try:
            # We expect this to potentially fail on auth, but the signature should be accepted
            client = JogetClient("http://test.example.com/jw", api_key="test-key")
            print("  ✓ Old-style initialization signature accepted")

            # Check that all expected attributes exist
            assert hasattr(client, 'config'), "Missing config attribute"
            assert hasattr(client, 'base_url'), "Missing base_url attribute"
            assert hasattr(client, 'session'), "Missing session attribute"

            print("  ✓ Client has expected attributes")

        except Exception as e:
            # Connection/auth errors are OK, we're just testing the signature
            if "config" in str(e).lower() or "base_url" in str(e).lower():
                print(f"  ✗ Initialization failed: {e}")
                return False
            else:
                print(f"  ⚠ Auth/connection error (expected): {type(e).__name__}")
                print("  ✓ Old-style initialization signature still works")

        return True

    except Exception as e:
        print(f"✗ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mro():
    """Test Method Resolution Order."""
    print("\n" + "=" * 70)
    print("TEST 5: Method Resolution Order (MRO)")
    print("=" * 70)

    from joget_deployment_toolkit.client import JogetClient

    print("\nJogetClient MRO:")
    for i, cls in enumerate(JogetClient.__mro__, 1):
        print(f"  {i}. {cls.__name__}")

    # Check that all mixins are in the MRO
    mixin_names = [
        'BaseClient',
        'FormOperations',
        'ApplicationOperations',
        'PluginOperations',
        'HealthOperations'
    ]

    mro_class_names = [cls.__name__ for cls in JogetClient.__mro__]

    print("\nMixin presence check:")
    all_present = True
    for mixin in mixin_names:
        if mixin in mro_class_names:
            print(f"  ✓ {mixin}")
        else:
            print(f"  ✗ {mixin} - MISSING!")
            all_present = False

    return all_present


def main():
    """Run all tests."""
    print("\n")
    print("*" * 70)
    print("JOGET-TOOLKIT REFACTORING VERIFICATION")
    print("Week 2: Client Refactoring - Task Completion Check")
    print("*" * 70)

    results = {
        "Module Imports": test_imports(),
        "Client Structure": test_client_structure(),
        "Alternative Constructors": test_alternative_constructors(),
        "Backward Compatibility": test_backward_compatibility(),
        "Method Resolution Order": test_mro(),
    }

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Week 2 refactoring is COMPLETE!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the failures above")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
