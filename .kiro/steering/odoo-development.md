---
inclusion: always
---

# Odoo 19.0 Development Guide

This steering file provides guidelines for developing Odoo modules, based on the official Odoo 19.0 documentation and the biotime_sync module structure.

## Environment Setup

### Source Installation (Recommended for Development)

Odoo development uses a source install approach with three repositories:
- `odoo/odoo` - Core Odoo framework
- `odoo/enterprise` - Enterprise features (if licensed)
- `odoo/tutorials` or custom addons directory - Custom modules

### Running the Server

```bash
# Basic launch
./odoo-bin -d <database> --addons-path=<directories>

# Common options
-d <database>           # Database to use
--addons-path <dirs>    # Comma-separated module directories
--limit-time-cpu <sec>  # CPU time limit per request
--limit-time-real <sec> # Real time limit per request
-u <module>             # Update module(s)
-i <module>             # Install module(s)
--dev=all               # Development mode with auto-reload
```

### Developer Mode

Enable developer mode in Odoo UI for access to advanced tools:
- Settings → General Settings → Developer Tools → Activate Developer Mode
- Or append `?debug=1` to URL

## Module Structure

Standard Odoo module layout (based on biotime_sync):

```
module_name/
├── __init__.py              # Python package init
├── __manifest__.py          # Module metadata
├── controllers/             # HTTP controllers
│   ├── __init__.py
│   └── main_controller.py
├── data/                    # Data files (XML/CSV)
│   └── cron.xml
├── models/                  # Business logic models
│   ├── __init__.py
│   └── model_name.py
├── security/                # Access control
│   ├── ir.model.access.csv  # Model access rights
│   └── security_groups.xml  # Security groups
├── static/                  # Web assets
│   └── src/
│       ├── css/
│       ├── js/
│       └── xml/             # QWeb templates
├── tests/                   # Unit tests
├── views/                   # UI definitions
│   ├── model_views.xml
│   └── menu.xml
└── wizard/                  # Transient models (wizards)
```

## Manifest File (__manifest__.py)

```python
{
    'name': 'Module Name',
    'version': '19.0.1.0.0',  # Format: odoo_version.major.minor.patch
    'category': 'Category/Subcategory',
    'summary': 'Short description',
    'description': """Long description with features""",
    'author': 'Author Name',
    'website': 'https://example.com',
    'license': 'LGPL-3',  # Common: LGPL-3, AGPL-3, OPL-1
    'depends': ['base', 'hr'],  # Required dependencies
    'data': [
        'security/security_groups.xml',  # Load order matters!
        'security/ir.model.access.csv',
        'data/cron.xml',
        'wizard/wizard_views.xml',
        'views/model_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'module_name/static/src/css/style.css',
            'module_name/static/src/js/script.js',
            'module_name/static/src/xml/template.xml',
        ],
    },
    'installable': True,
    'application': True,  # True if standalone app
    'auto_install': False,
}
```

## Model Definition

### Standard Model

```python
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ModelName(models.Model):
    _name = 'module.model'
    _description = 'Model Description'
    _order = 'date desc, name'
    _rec_name = 'name'  # Field used for display_name

    # Basic fields
    name = fields.Char(string='Name', required=True, index=True)
    active = fields.Boolean(default=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    datetime_field = fields.Datetime(default=fields.Datetime.now)
    
    # Selection field
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)
    
    # Relational fields
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade')
    line_ids = fields.One2many('module.model.line', 'parent_id', string='Lines')
    tag_ids = fields.Many2many('module.tag', string='Tags')
    
    # Computed field
    total = fields.Float(compute='_compute_total', store=True)
    
    # SQL constraints
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Name must be unique!'),
    ]

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for record in self:
            record.total = sum(record.line_ids.mapped('amount'))

    @api.constrains('date')
    def _check_date(self):
        for record in self:
            if record.date and record.date > fields.Date.today():
                raise ValidationError(_("Date cannot be in the future."))

    @api.model
    def create(self, vals):
        # Custom create logic
        return super().create(vals)

    def write(self, vals):
        # Custom write logic
        return super().write(vals)

    def action_confirm(self):
        """Button action method."""
        self.ensure_one()
        self.state = 'confirmed'
```

### Inherited Model

```python
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    custom_field = fields.Char(string='Custom Field')
```

## Views (XML)

### Form View

```xml
<record id="view_model_form" model="ir.ui.view">
    <field name="name">module.model.form</field>
    <field name="model">module.model</field>
    <field name="arch" type="xml">
        <form string="Model">
            <header>
                <button name="action_confirm" type="object" 
                        string="Confirm" class="btn-primary"
                        invisible="state != 'draft'"/>
                <field name="state" widget="statusbar"/>
            </header>
            <sheet>
                <group>
                    <group>
                        <field name="name"/>
                        <field name="partner_id"/>
                    </group>
                    <group>
                        <field name="date"/>
                        <field name="total"/>
                    </group>
                </group>
                <notebook>
                    <page string="Lines">
                        <field name="line_ids">
                            <list editable="bottom">
                                <field name="name"/>
                                <field name="amount"/>
                            </list>
                        </field>
                    </page>
                </notebook>
            </sheet>
            <chatter/>
        </form>
    </field>
</record>
```

### List/Tree View

```xml
<record id="view_model_list" model="ir.ui.view">
    <field name="name">module.model.list</field>
    <field name="model">module.model</field>
    <field name="arch" type="xml">
        <list string="Models" decoration-danger="state == 'draft'">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="date"/>
            <field name="state" widget="badge"/>
            <field name="total" sum="Total"/>
        </list>
    </field>
</record>
```

### Search View

```xml
<record id="view_model_search" model="ir.ui.view">
    <field name="name">module.model.search</field>
    <field name="model">module.model</field>
    <field name="arch" type="xml">
        <search string="Search">
            <field name="name"/>
            <field name="partner_id"/>
            <filter name="filter_draft" string="Draft" 
                    domain="[('state', '=', 'draft')]"/>
            <separator/>
            <filter name="filter_today" string="Today" 
                    domain="[('date', '=', context_today().strftime('%Y-%m-%d'))]"/>
            <group expand="0" string="Group By">
                <filter name="group_state" string="Status" 
                        context="{'group_by': 'state'}"/>
            </group>
        </search>
    </field>
</record>
```

### Action and Menu

```xml
<record id="action_model" model="ir.actions.act_window">
    <field name="name">Models</field>
    <field name="res_model">module.model</field>
    <field name="view_mode">list,form</field>
    <field name="context">{'search_default_filter_draft': 1}</field>
    <field name="help" type="html">
        <p class="o_view_nocontent_smiling_face">
            Create your first record
        </p>
    </field>
</record>

<menuitem id="menu_root" name="Module" sequence="10"/>
<menuitem id="menu_model" name="Models" 
          parent="menu_root" action="action_model" sequence="10"/>
```

## Security

### Security Groups (security_groups.xml)

```xml
<odoo>
    <record id="group_user" model="res.groups">
        <field name="name">User</field>
        <field name="category_id" ref="base.module_category_hidden"/>
    </record>
    
    <record id="group_manager" model="res.groups">
        <field name="name">Manager</field>
        <field name="category_id" ref="base.module_category_hidden"/>
        <field name="implied_ids" eval="[(4, ref('group_user'))]"/>
    </record>
</odoo>
```

### Access Rights (ir.model.access.csv)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_model_user,module.model.user,model_module_model,group_user,1,0,0,0
access_model_manager,module.model.manager,model_module_model,group_manager,1,1,1,1
```

## Controllers (HTTP Routes)

```python
from odoo import http
from odoo.http import request

class MainController(http.Controller):

    @http.route('/module/endpoint', type='json', auth='user')
    def json_endpoint(self, param1=None):
        """JSON-RPC endpoint for AJAX calls."""
        Model = request.env['module.model']
        records = Model.search([])
        return {'data': records.read(['name', 'total'])}

    @http.route('/module/page', type='http', auth='public', website=True)
    def http_page(self):
        """HTTP endpoint returning HTML."""
        return request.render('module.template_name', {})
```

## Scheduled Actions (Cron)

```xml
<odoo>
    <record id="ir_cron_sync" model="ir.cron">
        <field name="name">Module: Daily Sync</field>
        <field name="model_id" ref="model_module_model"/>
        <field name="state">code</field>
        <field name="code">model.cron_sync()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">days</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
</odoo>
```

## Wizards (Transient Models)

```python
class SyncWizard(models.TransientModel):
    _name = 'module.sync.wizard'
    _description = 'Sync Wizard'

    date_from = fields.Date(required=True, default=fields.Date.today)
    date_to = fields.Date(required=True, default=fields.Date.today)

    def action_sync(self):
        """Execute sync and return notification."""
        self.ensure_one()
        # Perform sync logic
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Sync completed successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }
```

## Python Debugging

### Using ipdb

```bash
pip install ipdb
```

```python
# Add breakpoint in code
import ipdb; ipdb.set_trace()
```

### Debugger Commands

- `h(elp)` - Show help
- `n(ext)` - Next line
- `s(tep)` - Step into
- `c(ontinue)` - Continue execution
- `pp expression` - Pretty print
- `w(here)` - Stack trace
- `u(p)` / `d(own)` - Navigate stack
- `q(uit)` - Quit debugger

## Code Standards

### Python (PEP8 with Odoo exceptions)

Ignored rules: E501 (line length), E301, E302 (blank lines)

### JavaScript (ESLint)

Use Odoo's ESLint configuration for frontend code.

## Best Practices

1. **Always use `self.ensure_one()`** for methods expecting single records
2. **Use `_()` for translatable strings**: `from odoo import _`
3. **Handle exceptions properly**: Use `UserError` for user-facing errors
4. **Use computed fields with `store=True`** for frequently accessed data
5. **Add indexes** to frequently searched fields: `index=True`
6. **Use `ondelete='cascade'`** or `'restrict'` for Many2one fields
7. **Order data files correctly** in manifest (security before views)
8. **Use `sudo()`** sparingly and only when necessary
9. **Log important operations**: `_logger.info()`, `_logger.warning()`, `_logger.error()`
10. **Write SQL constraints** for database-level validation

## Testing

```bash
# Run tests for a module
./odoo-bin -d test_db -i module_name --test-enable --stop-after-init

# Run specific test
./odoo-bin -d test_db --test-tags /module_name:TestClassName
```

## Configuration Model Pattern

For modules requiring settings/configuration, use a singleton pattern with the following structure:

### Model Definition

```python
class ModuleConfig(models.Model):
    _name = 'module.config'
    _description = 'Module Configuration'
    _rec_name = 'name'
    
    # General Settings
    name = fields.Char(string='Configuration Name', required=True, default='Main Configuration')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    
    # API/Connection Settings
    api_url = fields.Char(string='API URL', required=True)
    api_port = fields.Integer(string='API Port', default=443)
    auth_method = fields.Selection([
        ('token', 'Token'),
        ('jwt', 'JWT'),
        ('basic', 'Basic'),
    ], string='Auth Method', required=True, default='token')
    api_token = fields.Char(string='API Token')
    username = fields.Char(string='Username')
    password = fields.Char(string='Password')
    timeout = fields.Integer(string='Timeout (seconds)', default=30)
    
    # Timezone
    timezone = fields.Selection(
        selection='_get_timezone_selection',
        string='Timezone',
        default='UTC'
    )
    
    # Business Rules
    # ... domain-specific settings ...
    
    # Sync Settings
    auto_sync_enabled = fields.Boolean(string='Enable Auto Sync', default=True)
    sync_interval = fields.Integer(string='Sync Interval (hours)', default=1)
    sync_days_back = fields.Integer(string='Sync Days Back', default=1)
    
    # Last Sync Info (readonly)
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('partial', 'Partial'),
    ], string='Last Sync Status', readonly=True)
    last_sync_message = fields.Text(string='Last Sync Message', readonly=True)
    
    @api.model
    def _get_timezone_selection(self):
        import pytz
        return [(tz, tz) for tz in pytz.common_timezones]
    
    @api.model
    def get_config(self):
        """Get singleton configuration record."""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Main Configuration'})
        return config
    
    def _update_last_sync_info(self, status, message=None):
        """Update last sync information."""
        self.ensure_one()
        self.write({
            'last_sync_date': fields.Datetime.now(),
            'last_sync_status': status,
            'last_sync_message': message or '',
        })
    
    def test_connection(self):
        """Test API connection."""
        self.ensure_one()
        try:
            # Connection test logic
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Successfully connected.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
```

### Configuration Form View with Tabs

```xml
<record id="view_module_config_form" model="ir.ui.view">
    <field name="name">module.config.form</field>
    <field name="model">module.config</field>
    <field name="arch" type="xml">
        <form string="Configuration">
            <header>
                <button name="test_connection" type="object" 
                        string="Test Connection" class="btn-primary" icon="fa-plug"/>
                <button name="action_sync" type="object" 
                        string="Sync Now" class="btn-secondary" icon="fa-refresh"/>
            </header>
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <button name="action_view_logs" type="object"
                            class="oe_stat_button" icon="fa-history">
                        <span class="o_stat_text">Logs</span>
                    </button>
                </div>
                <widget name="web_ribbon" title="Archived" bg_color="text-bg-danger" 
                        invisible="active"/>
                <div class="oe_title">
                    <label for="name"/>
                    <h1><field name="name" placeholder="Configuration Name"/></h1>
                </div>
                <group>
                    <group>
                        <field name="company_id" groups="base.group_multi_company"/>
                        <field name="active" invisible="1"/>
                    </group>
                    <group>
                        <field name="timezone"/>
                    </group>
                </group>
                <notebook>
                    <page string="API Connection" name="api">
                        <group>
                            <group string="Server">
                                <field name="api_url"/>
                                <field name="api_port"/>
                                <field name="timeout"/>
                            </group>
                            <group string="Authentication">
                                <field name="auth_method"/>
                                <field name="api_token" password="True" 
                                       invisible="auth_method != 'token'"
                                       required="auth_method == 'token'"/>
                                <field name="username" 
                                       invisible="auth_method == 'token'"
                                       required="auth_method != 'token'"/>
                                <field name="password" password="True" 
                                       invisible="auth_method == 'token'"
                                       required="auth_method != 'token'"/>
                            </group>
                        </group>
                    </page>
                    <page string="Business Rules" name="rules">
                        <!-- Domain-specific settings -->
                    </page>
                    <page string="Synchronization" name="sync">
                        <group>
                            <group string="Auto Sync">
                                <field name="auto_sync_enabled"/>
                                <field name="sync_interval" invisible="not auto_sync_enabled"/>
                                <field name="sync_days_back"/>
                            </group>
                            <group string="Last Sync">
                                <field name="last_sync_date"/>
                                <field name="last_sync_status" widget="badge"
                                       decoration-success="last_sync_status == 'success'"
                                       decoration-danger="last_sync_status == 'error'"
                                       decoration-warning="last_sync_status == 'partial'"/>
                                <field name="last_sync_message"/>
                            </group>
                        </group>
                    </page>
                </notebook>
            </sheet>
        </form>
    </field>
</record>
```

### Key Configuration Patterns

1. **Singleton pattern**: Use `get_config()` to always get the active configuration
2. **Multi-company support**: Add `company_id` field with proper filtering
3. **Tabbed interface**: Organize settings in logical groups (API, Rules, Sync)
4. **Status tracking**: Track last sync date/status/message for monitoring
5. **Conditional fields**: Show/hide fields based on auth_method selection
6. **Action buttons**: Test connection, manual sync, view logs
7. **Stat buttons**: Quick access to related records (logs, etc.)

## Current Module: biotime_sync

This workspace contains the `biotime_sync` module for integrating Odoo with ZKTeco Biotime biometric attendance systems.

### Key Models
- `biotime.config` - API configuration and sync engine (singleton pattern)
- `biotime.attendance` - Attendance records with computed fields
- `biotime.sync.log` - Synchronization history
- `hr.employee` (inherited) - Added biotime_id field

### Configuration Fields (biotime.config)
- **General**: name, active, company_id, timezone
- **API**: api_url, api_port, auth_method, api_token, username, password, timeout
- **Business Rules**: work_start_time, work_end_time, break_duration, late_tolerance, overtime_threshold
- **Sync**: auto_sync_enabled, sync_interval, sync_days_back
- **Status**: last_sync_date, last_sync_status, last_sync_message

### Features
- Multi-auth support (Token, JWT, Basic)
- Paginated API fetching
- Employee matching by biotime_id or barcode
- Automatic worked hours, late detection, overtime calculation
- Dashboard with statistics endpoints
- Role-based access (User, Supervisor, Manager)
- Configurable auto-sync with status tracking
