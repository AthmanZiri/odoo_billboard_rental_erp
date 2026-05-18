/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { Component, onWillStart, useState } from "@odoo/owl";

export class MediaExecutiveDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.display = {
            controlPanel: { "top-right": false, "bottom-right": false },
        };
        this.state = useState({
            loading: true,
            data: null,
            error: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call(
                "media.executive.dashboard",
                "get_dashboard_data",
                []
            );
        } catch (e) {
            this.state.error = e.message || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this.loadData();
    }

    async onDrilldown(key) {
        const action = await this.orm.call(
            "media.executive.dashboard",
            "action_drilldown",
            [key]
        );
        if (action && action.type) {
            await this.action.doAction(action);
        }
    }

    formatMoney(amount) {
        const c = this.state.data?.currency;
        if (!c || amount == null) {
            return "—";
        }
        const n = Number(amount);
        const formatted = n.toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
        return c.position === "after"
            ? `${formatted} ${c.symbol}`
            : `${c.symbol} ${formatted}`;
    }

    formatPct(value, digits = 1) {
        if (value == null) {
            return "—";
        }
        return `${Number(value).toFixed(digits)}%`;
    }

    formatDelta(value, suffix = "") {
        if (value == null) {
            return null;
        }
        const n = Number(value);
        const sign = n > 0 ? "+" : "";
        return `${sign}${n.toFixed(1)}${suffix}`;
    }

    deltaClass(value) {
        if (value == null || value === 0) {
            return "text-muted";
        }
        return value > 0 ? "text-success" : "text-danger";
    }

    occupancyTotal() {
        const o = this.state.data?.occupancy;
        if (!o) {
            return 0;
        }
        return o.available + o.booked + o.reserved + o.maintenance;
    }

    occupancyPct(key) {
        const total = this.occupancyTotal();
        if (!total) {
            return 0;
        }
        return (100 * (this.state.data.occupancy[key] || 0)) / total;
    }

    maxCountyUtil() {
        const counties = this.state.data?.counties || [];
        return Math.max(1, ...counties.map((c) => c.occupancy_pct || 0));
    }

    countyBarWidth(pct) {
        const max = this.maxCountyUtil();
        return Math.max(4, (100 * (pct || 0)) / max);
    }

    trendPoints() {
        const trend = this.state.data?.trend || [];
        if (trend.length < 2) {
            return "";
        }
        const maxY = Math.max(1, ...trend.map((t) => t.utilization_pct || 0));
        const w = 280;
        const h = 80;
        const pts = trend.map((t, i) => {
            const x = (i / (trend.length - 1)) * w;
            const y = h - ((t.utilization_pct || 0) / maxY) * h;
            return `${x},${y}`;
        });
        return pts.join(" ");
    }

    inboxDisplayCount(item) {
        if (item.is_money) {
            return this.formatMoney(item.count);
        }
        return item.count ?? 0;
    }
}

MediaExecutiveDashboard.template = "media_dashboard.ExecutiveDashboard";
MediaExecutiveDashboard.components = { Layout };

registry.category("actions").add(
    "media_dashboard.executive_dashboard",
    MediaExecutiveDashboard
);
