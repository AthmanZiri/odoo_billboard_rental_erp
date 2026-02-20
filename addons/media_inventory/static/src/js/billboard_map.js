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
        this.siteModel = this.props.action?.params?.model || "media.site";
        this.domain = this.props.action?.params?.domain || [];
        this.display = {
            controlPanel: { "top-right": true, "bottom-right": true },
        };

        onMounted(async () => {
            await this.initMap();
            await this.loadMarkers(this.domain);
        });

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
            }
        });

        onWillUpdateProps(async (nextProps) => {
            const nextDomain = nextProps.action?.params?.domain || [];
            if (JSON.stringify(this.domain) !== JSON.stringify(nextDomain)) {
                this.domain = nextDomain;
                await this.loadMarkers(this.domain);
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

        let fields = ["name", "code", "latitude", "longitude", "city", "county_id", "sub_county_id"];
        if (this.siteModel === "media.site") {
            fields.push("site_category", "shop_name");
        }

        const sites = await this.orm.searchRead(this.siteModel, domain || [], fields);

        sites.forEach(site => {
            if (!site.latitude || !site.longitude) return;

            let isCanopy = false;
            let isDigitalScreen = this.siteModel === 'media.digital.screen';
            let markerColor = '#007bff'; // Default Billboard Blue
            let iconClass = 'fa-picture-o';
            let categoryLabel = 'BILLBOARD';

            if (this.siteModel === 'media.site' && site.site_category === 'canopy') {
                isCanopy = true;
                markerColor = '#28a745'; // Canopy Green
                iconClass = 'fa-shopping-cart';
                categoryLabel = 'CANOPY';
            } else if (isDigitalScreen) {
                markerColor = '#dc3545'; // Digital Screen Red
                iconClass = 'fa-television';
                categoryLabel = 'DIGITAL SCREEN';
            }

            const customIcon = L.divIcon({
                className: 'custom-div-icon',
                html: `<div style="background-color: ${markerColor};" class="marker-pin"></div><i class="fa ${iconClass}"></i>`,
                iconSize: [30, 42],
                iconAnchor: [15, 42]
            });

            const popupContent = `
                <div class="site-popup">
                    <div class="popup-header" style="border-bottom: 2px solid ${markerColor}; color: ${markerColor};">
                        <strong>${site.name}</strong>
                        <span class="badge" style="background-color: ${markerColor};">${categoryLabel}</span>
                    </div>
                    <div class="popup-body mt-2">
                        ${isCanopy && site.shop_name ? `<div><strong>Shop:</strong> ${site.shop_name}</div>` : ''}
                        <div><strong>Code:</strong> ${site.code || 'N/A'}</div>
                        <div><strong>Location:</strong> ${site.sub_county_id ? site.sub_county_id[1] : ''}, ${site.county_id ? site.county_id[1] : ''}</div>
                    </div>
                    <button class="btn btn-primary btn-sm mt-2 w-100" onclick="window.odoo_open_site(${site.id}, '${this.siteModel}')">
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
        window.odoo_open_site = (siteId, model) => {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: model,
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
