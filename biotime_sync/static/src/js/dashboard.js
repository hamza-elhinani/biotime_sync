/** @odoo-module **/
/**
 * Biotime Dashboard OWL Component for Odoo 19
 */

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class BiotimeDashboard extends Component {
    static template = "biotime_sync.Dashboard";
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            stats: {
                total_employees: 0,
                present_count: 0,
                absent_count: 0,
                late_count: 0,
                incomplete_count: 0,
                total_worked_hours: 0,
                synced_count: 0,
                not_synced_count: 0,
            },
            recentAttendance: [],
            topLate: [],
            loading: true,
            error: null,
            lastSyncDate: null,
            lastSyncStatus: null,
        });
        
        onWillStart(async () => {
            await this._loadAllData();
        });
    }
    
    async _loadAllData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            await Promise.all([
                this._loadStats(),
                this._loadRecentAttendance(),
                this._loadTopLate(),
                this._loadSyncInfo(),
            ]);
        } catch (error) {
            console.error("Failed to load dashboard data:", error);
            this.state.error = _t("Failed to load dashboard data");
        } finally {
            this.state.loading = false;
        }
    }
    
    async _loadStats() {
        // Get today's date
        const today = new Date().toISOString().split('T')[0];
        
        // Count total active employees
        const totalEmployees = await this.orm.searchCount("hr.employee", [['active', '=', true]]);
        this.state.stats.total_employees = totalEmployees;
        
        // Count today's attendance by status
        const presentCount = await this.orm.searchCount("biotime.attendance", [
            ['date', '=', today],
            ['status', '=', 'present']
        ]);
        
        const lateCount = await this.orm.searchCount("biotime.attendance", [
            ['date', '=', today],
            ['status', '=', 'late']
        ]);
        
        const incompleteCount = await this.orm.searchCount("biotime.attendance", [
            ['date', '=', today],
            ['status', '=', 'incomplete']
        ]);
        
        const totalTodayRecords = await this.orm.searchCount("biotime.attendance", [
            ['date', '=', today]
        ]);
        
        // Synced counts
        const syncedCount = await this.orm.searchCount("biotime.attendance", [
            ['synced_to_hr', '=', true]
        ]);
        
        const notSyncedCount = await this.orm.searchCount("biotime.attendance", [
            ['synced_to_hr', '=', false],
            ['check_in', '!=', false]
        ]);
        
        // Get total worked hours today
        const todayAttendances = await this.orm.searchRead(
            "biotime.attendance",
            [['date', '=', today]],
            ['worked_hours']
        );
        const totalWorkedHours = todayAttendances.reduce((sum, att) => sum + (att.worked_hours || 0), 0);
        
        this.state.stats.present_count = presentCount;
        this.state.stats.late_count = lateCount;
        this.state.stats.incomplete_count = incompleteCount;
        this.state.stats.absent_count = Math.max(0, totalEmployees - totalTodayRecords);
        this.state.stats.total_worked_hours = totalWorkedHours.toFixed(1);
        this.state.stats.synced_count = syncedCount;
        this.state.stats.not_synced_count = notSyncedCount;
    }
    
    async _loadRecentAttendance() {
        const records = await this.orm.searchRead(
            "biotime.attendance",
            [],
            ['employee_id', 'date', 'check_in', 'check_out', 'status', 'worked_hours', 'synced_to_hr'],
            { limit: 10, order: 'date desc, check_in desc' }
        );
        this.state.recentAttendance = records;
    }
    
    async _loadTopLate() {
        // Get last 7 days late records
        const today = new Date();
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);
        const weekAgoStr = weekAgo.toISOString().split('T')[0];
        
        const lateRecords = await this.orm.searchRead(
            "biotime.attendance",
            [['date', '>=', weekAgoStr], ['is_late', '=', true]],
            ['employee_id', 'late_minutes'],
            { order: 'late_minutes desc' }
        );
        
        // Aggregate by employee
        const employeeLate = {};
        for (const record of lateRecords) {
            const empId = record.employee_id[0];
            const empName = record.employee_id[1];
            if (!employeeLate[empId]) {
                employeeLate[empId] = { name: empName, count: 0, totalMinutes: 0 };
            }
            employeeLate[empId].count++;
            employeeLate[empId].totalMinutes += record.late_minutes || 0;
        }
        
        // Sort and take top 5
        this.state.topLate = Object.values(employeeLate)
            .sort((a, b) => b.count - a.count)
            .slice(0, 5);
    }
    
    async _loadSyncInfo() {
        const configs = await this.orm.searchRead(
            "biotime.config",
            [['active', '=', true]],
            ['last_sync_date', 'last_sync_status'],
            { limit: 1 }
        );
        if (configs.length > 0) {
            this.state.lastSyncDate = configs[0].last_sync_date;
            this.state.lastSyncStatus = configs[0].last_sync_status;
        }
    }
    
    get presenceRate() {
        const total = this.state.stats.total_employees;
        if (!total) return 0;
        const present = this.state.stats.present_count + this.state.stats.late_count;
        return Math.round((present / total) * 100);
    }
    
    get syncRate() {
        const total = this.state.stats.synced_count + this.state.stats.not_synced_count;
        if (!total) return 100;
        return Math.round((this.state.stats.synced_count / total) * 100);
    }
    
    formatTime(datetime) {
        if (!datetime) return '-';
        const date = new Date(datetime);
        return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }
    
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    }
    
    formatHours(hours) {
        if (!hours) return '0:00';
        const h = Math.floor(hours);
        const m = Math.round((hours - h) * 60);
        return `${h}:${m.toString().padStart(2, '0')}`;
    }
    
    getStatusClass(status) {
        const classes = {
            'present': 'bg-success',
            'late': 'bg-warning',
            'absent': 'bg-danger',
            'incomplete': 'bg-secondary',
            'half_day': 'bg-info',
        };
        return classes[status] || 'bg-secondary';
    }
    
    getStatusLabel(status) {
        const labels = {
            'present': _t('Present'),
            'late': _t('Late'),
            'absent': _t('Absent'),
            'incomplete': _t('Incomplete'),
            'half_day': _t('Half Day'),
        };
        return labels[status] || status;
    }
    
    async onRefresh() {
        await this._loadAllData();
        this.notification.add(_t("Dashboard refreshed"), { type: "success" });
    }
    
    async onSyncEmployees() {
        try {
            const configs = await this.orm.search("biotime.config", [['active', '=', true]], { limit: 1 });
            if (configs.length > 0) {
                await this.orm.call("biotime.config", "action_sync_employees", [configs]);
                await this._loadAllData();
            }
        } catch (error) {
            this.notification.add(_t("Sync failed: ") + error.message, { type: "danger" });
        }
    }
    
    async onSyncToHR() {
        try {
            const result = await this.orm.call("biotime.attendance", "sync_all_to_hr_attendance", []);
            await this._loadAllData();
            this.notification.add(_t("Sync to HR Attendance completed"), { type: "success" });
        } catch (error) {
            this.notification.add(_t("Sync failed: ") + error.message, { type: "danger" });
        }
    }
    
    onViewAttendance() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Attendance'),
            res_model: 'biotime.attendance',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
        });
    }
    
    onViewHRAttendance() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('HR Attendance'),
            res_model: 'hr.attendance',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
        });
    }
    
    onViewNotSynced() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Not Synced Attendance'),
            res_model: 'biotime.attendance',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [['synced_to_hr', '=', false], ['check_in', '!=', false]],
        });
    }
}

registry.category("actions").add("biotime_dashboard", BiotimeDashboard);
