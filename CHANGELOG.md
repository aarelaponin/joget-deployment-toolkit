# Changelog

All notable changes to joget-deployment-toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-22

### Added

#### FormCreator Plugin Integration
- **`deploy_form()`**: Deploy forms via FormCreator API plugin with automatic table creation and cache invalidation
- Plugin handles: database table creation, Joget cache refresh, optional CRUD scaffolding
- Endpoint: `POST /jw/api/formcreator/formcreator/forms` (note the doubled path - quirk of Joget API routing)

#### Component Deployment
- **`ComponentDeployer`**: Deploy complete components (MDM + forms) in correct dependency order
- Validates component structure before deployment
- Returns detailed deployment results per component

#### Instance Migration
- **`InstanceMigrator`**: Migrate forms, datalists, data, and userview menus between Joget instances
- **`analyze()`**: Dry-run to preview what would be migrated
- **`migrate_app_component()`**: Full migration with optional data transfer
- CLI support: `joget-deploy migrate --source jdx3 --target jdx4 ...`

#### Inventory API
- **`list_instances()`**: List all configured instances with running status
- **`get_instance_status()`**: Check single instance health with response time
- **`get_apps_overview()`**: Get applications across multiple instances
- **`compare_apps()`**: Compare applications between environments (staging vs production)
- **`JogetClient.check_instance()`**: Class method for quick connectivity checks

#### Datalist & Userview Operations
- **`list_datalists()`**, **`get_datalist()`**, **`create_datalist()`**, **`update_datalist()`**, **`delete_datalist()`**
- **`list_userviews()`**, **`get_userview()`**, **`update_userview()`**
- **`create_crud_menu()`**: Generate CrudMenu configuration for datalist + form
- **`add_menu_to_category()`**: Add menu items to existing userview categories

#### Data Loading Utilities
- **`CSVDataLoader`**: Load CSV files for MDM deployment
- **`CSVDataLoader.add_column_prefix()`**: Add form ID prefix to column names

#### MDM Deployment
- **`PluginMDMDeployer`**: Deploy MDM forms using FormCreator plugin API
- **`MDMDataDeployer`**: Deploy MDM forms with CSV data from directories

### Improved

- **SessionAuth**: Updated for Joget 9.x OWASP CSRFGuard compatibility
- **Response parsing**: Handle nested JSON responses from FormCreator plugin
- **Error messages**: More descriptive errors for API failures

### Documentation

- Added FormCreator Plugin Integration section to CLAUDE.md
- Added Menu Types documentation (CrudMenu vs FormMenu)
- Added Datalist naming conventions
- Added Migration checklist

---

## [1.0.0] - 2025-12-16

### Initial Release

This is the first release of **joget-deployment-toolkit**, a focused refactoring of the former `joget-toolkit` package.

### Core Features

#### REST API Client
- **`JogetClient`**: Type-safe REST API client with multiple authentication strategies
- **Mixin Architecture**: Modular operations (Forms, Applications, Data)
- **`from_instance()`**: Zero-config client creation from shared configuration
- **`from_credentials()`**: Direct username/password authentication
- **`from_config()`**: Configuration object-based initialization

#### Authentication
- **`SessionAuth`**: Session-based authentication with CSRF handling
- **`APIKeyAuth`**: API key authentication
- **`BasicAuth`**: HTTP Basic authentication
- **`NoAuth`**: For unauthenticated endpoints

#### Form Operations
- **`list_forms()`**: List all forms in an application
- **`get_form()`**: Get form definition JSON
- **`create_form()`**: Create new form
- **`update_form()`**: Update existing form
- **`delete_form()`**: Delete form

#### Application Operations
- **`list_applications()`**: List all applications
- **`export_application()`**: Export app to ZIP file
- **`import_application()`**: Import app from ZIP file

#### Data Operations
- **`submit_form_data()`**: Submit data to a form
- **`submit_batch()`**: Batch data submission

#### Form Discovery
- **`FormDiscovery`**: Extract form definitions from Joget MySQL database
- Connection pooling for efficient database access
- Repository pattern for clean data access

### Configuration

#### Shared Config Integration
- Reads from `~/.joget/instances.yaml` (managed by joget-instance-manager)
- Password references via environment variables (`password_env: JDX4_PASSWORD`)
- Supports multiple instances (jdx1-jdx6+)

### Error Handling

- **`JogetAPIError`**: Base exception
- **`AuthenticationError`**: 401/403 responses
- **`NotFoundError`**: 404 responses
- **`ValidationError`**: 400 responses
- **`ConflictError`**: 409 responses
- **`ServerError`**: 500+ responses
- **`TimeoutError`**: Request timeout
- **`BatchError`**: Batch operation failures

### Breaking Changes from joget-toolkit

- Package renamed from `joget-toolkit` to `joget-deployment-toolkit`
- Config location changed: `~/.frs-dev/config.yaml` → `~/.joget/instances.yaml`
- Removed FRS Platform integration (replaced with shared config)
- Removed health check operations (use joget-instance-manager)
- Removed plugin discovery (not deployment-related)

---

[1.1.0]: https://github.com/aarelaponin/joget-deployment-toolkit/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/aarelaponin/joget-deployment-toolkit/releases/tag/v1.0.0
