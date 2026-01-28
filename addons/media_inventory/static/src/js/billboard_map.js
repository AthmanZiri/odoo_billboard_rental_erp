/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useRef, onWillUnmount } from "@odoo/owl";

export class BillboardMap extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.markers = [];

        onMounted(() => {
            this.initMap();
        });

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
            }
        });
    }

    async initMap() {
        // Initialize the map centered on a default location (e.g., Mombasa area if known, or 0,0)
        this.map = L.map(this.mapContainer.el).setView([-4.0435, 39.6682], 12);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        await this.loadMarkers();
    }

    async loadMarkers() {
        const sites = await this.orm.searchRead("media.site", [
            ["latitude", "!=", 0],
            ["longitude", "!=", 0]
        ], ["name", "code", "latitude", "longitude", "city"]);

        sites.forEach(site => {
            const marker = L.marker([site.latitude, site.longitude])
                .addTo(this.map)
                .bindPopup(`
                    <div class="site-popup">
                        <strong>${site.name}</strong><br/>
                        Code: ${site.code || 'N/A'}<br/>
                        City: ${site.city || 'N/A'}<br/>
                        <button class="btn btn-primary btn-sm mt-1" onclick="window.odoo_open_site(${site.id})">
                            Open Site
                        </button>
                    </div>
                `);
            this.markers.push(marker);
        });

        // Add global helper to open site from popup
        window.odoo_open_site = (siteId) => {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'media.site',
                res_id: siteId,
                views: [[false, 'form']],
                target: 'current',
            });
        };
    }
}

BillboardMap.template = "media_inventory.BillboardMap";

// Register the action
registry.category("actions").add("media_inventory.billboard_map_action", BillboardMap);
