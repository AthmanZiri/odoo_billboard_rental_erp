/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { Component, onMounted, useRef, onWillUnmount, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class BillboardMap extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.markers = [];
        this.siteModel = "media.site";
        this.display = {
            controlPanel: { "top-right": true, "bottom-right": true },
        };

        onMounted(async () => {
            await this.initMap();
            await this.loadMarkers(this.props.domain || []);
        });

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
            }
        });

        onWillUpdateProps(async (nextProps) => {
            if (JSON.stringify(this.props.domain) !== JSON.stringify(nextProps.domain)) {
                await this.loadMarkers(nextProps.domain);
            }
        });
    }

    async initMap() {
        this.map = L.map(this.mapContainer.el).setView([-4.0435, 39.6682], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
    }

    async loadMarkers(domain = []) {
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.markers = [];

        const sites = await this.orm.searchRead(this.siteModel, domain || [],
            ["name", "code", "latitude", "longitude", "city", "site_category", "shop_name", "county_id", "sub_county_id", "canopy_status"]);

        sites.forEach(site => {
            const isCanopy = site.site_category === 'canopy';
            const markerColor = isCanopy ? '#28a745' : '#007bff';

            const customIcon = L.divIcon({
                className: 'custom-div-icon',
                html: `<div style="background-color: ${markerColor};" class="marker-pin"></div><i class="fa ${isCanopy ? 'fa-shopping-cart' : 'fa-television'}"></i>`,
                iconSize: [30, 42],
                iconAnchor: [15, 42]
            });

            const popupContent = `
                <div class="site-popup">
                    <div class="popup-header" style="border-bottom: 2px solid ${markerColor}; color: ${markerColor};">
                        <strong>${site.name}</strong>
                        ${site.site_category ? `<span class="badge" style="background-color: ${markerColor};">${site.site_category.toUpperCase()}</span>` : ''}
                    </div>
                    <div class="popup-body mt-2">
                        ${isCanopy && site.shop_name ? `<div><strong>Shop:</strong> ${site.shop_name}</div>` : ''}
                        <div><strong>Code:</strong> ${site.code || 'N/A'}</div>
                        <div><strong>Location:</strong> ${site.sub_county_id ? site.sub_county_id[1] : ''}, ${site.county_id ? site.county_id[1] : ''}</div>
                        ${isCanopy ? `<div><strong>Status:</strong> <span class="text-capitalize">${site.canopy_status || 'N/A'}</span></div>` : ''}
                    </div>
                    <button class="btn btn-primary btn-sm mt-2 w-100" onclick="window.odoo_open_site(${site.id})">
                        Open details
                    </button>
                </div>
            `;

            const marker = L.marker([site.latitude, site.longitude], { icon: customIcon })
                .addTo(this.map)
                .bindPopup(popupContent);
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
BillboardMap.components = { Layout };

// Register the action
registry.category("actions").add("media_inventory.billboard_map_action", BillboardMap);
