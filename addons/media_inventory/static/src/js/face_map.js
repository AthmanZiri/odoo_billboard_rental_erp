/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { Component, onMounted, useRef, onWillUnmount, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class FaceMap extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.markers = [];
        this.faceModel = "media.face";
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

        // We fetch faces, but we need their site's coordinates
        const faces = await this.orm.searchRead(this.faceModel, domain || [],
            ["name", "code", "face_type", "occupancy_status", "site_id"]
        );

        if (faces.length === 0) return;

        const siteIds = [...new Set(faces.map(f => f.site_id[0]))];
        const sites = await this.orm.searchRead('media.site', [['id', 'in', siteIds]],
            ["name", "site_category", "latitude", "longitude", "city", "county_id", "sub_county_id", "shop_name", "code"]
        );

        const sitesById = {};
        sites.forEach(s => sitesById[s.id] = s);

        // Group faces by site
        const facesBySite = {};
        faces.forEach(face => {
            const sId = face.site_id[0];
            if (!facesBySite[sId]) facesBySite[sId] = [];
            facesBySite[sId].push(face);
        });

        Object.keys(facesBySite).forEach(siteId => {
            const site = sitesById[siteId];
            if (!site || !site.latitude || !site.longitude) return;

            let lat = site.latitude;
            let lng = site.longitude;
            const siteFaces = facesBySite[siteId];
            const category = site.site_category || 'billboard';

            // Determine aggregate marker color
            let anyAvailable = false;
            let allBooked = true;
            siteFaces.forEach(f => {
                if (f.occupancy_status !== 'booked') allBooked = false;
                if (f.occupancy_status === 'available') anyAvailable = true;
            });

            let markerColor = '#28a745'; // Available Green
            if (allBooked && siteFaces.length > 0) {
                markerColor = '#dc3545'; // Booked Red
            } else if (!anyAvailable && !allBooked) {
                markerColor = '#ffc107'; // Yellow (Maintenance / Mixed)
            }

            let iconClass = 'fa-tag';
            if (category === 'canopy') {
                iconClass = 'fa-shopping-cart';
            } else if (category === 'digital') {
                iconClass = 'fa-television';
            }

            const customIcon = L.divIcon({
                className: 'custom-div-icon',
                html: `<div style="background-color: ${markerColor};" class="marker-pin"></div><i class="fa ${iconClass}"></i>`,
                iconSize: [24, 34],
                iconAnchor: [12, 34]
            });

            // Build popup body with all faces for this site
            let facesHtml = '';
            // If multiple faces, show them in a neat vertical list or horizontal scroll block
            facesHtml = `<div style="display: flex; flex-wrap: nowrap; gap: 10px; overflow-x: auto; padding-bottom: 5px; margin-bottom: 10px; max-width: 300px;">`;

            siteFaces.forEach(face => {
                let statusBg = face.occupancy_status === 'booked' ? '#dc3545' : '#28a745';
                let statusText = face.occupancy_status === 'booked' ? 'Booked' : 'Available';
                let categoryLabel = face.face_type ? face.face_type.replace('_', ' ').toUpperCase() : 'FACE';

                facesHtml += `
                    <div style="min-width: 140px; border: 1px solid #ddd; border-radius: 4px; padding: 5px; text-align: center; position: relative;">
                        <span style="position: absolute; top: 5px; right: 5px; background: ${statusBg}; color: white; font-size: 8px; padding: 2px 4px; border-radius: 2px;">
                            ${statusText}
                        </span>
                        <img src="/web/image/media.face/${face.id}/face_image" style="width: 100%; height: 80px; object-fit: cover; border-radius: 2px; margin-bottom: 5px;" onerror="this.onerror=null; this.src='/web/image/media.site/${site.id}/main_image';" />
                        <div style="font-size: 11px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${face.name}">${face.name}</div>
                        <div style="font-size: 10px; color: #666;">${categoryLabel}</div>
                        <button class="btn btn-sm btn-outline-primary w-100 mt-1" style="font-size: 10px; padding: 2px 5px;" onclick="window.odoo_open_face(${face.id})">Details</button>
                    </div>
                `;
            });
            facesHtml += `</div>`;


            const popupContent = `
                <div class="site-popup">
                    <div class="popup-header" style="border-bottom: 2px solid ${markerColor}; color: ${markerColor};">
                        <strong>${site.name} ${site.code ? '[' + site.code + ']' : ''}</strong>
                    </div>
                    <div class="popup-body mt-2">
                        ${facesHtml}
                        <div style="font-size: 11px;"><strong>Location:</strong> ${site.sub_county_id ? site.sub_county_id[1] : ''}, ${site.county_id ? site.county_id[1] : ''}</div>
                    </div>
                    <button class="btn btn-outline-secondary btn-sm mt-1 w-100" onclick="window.odoo_open_site_from_face(${site.id}, '${category}')">
                        View Site Record
                    </button>
                </div>
            `;

            const marker = L.marker([lat, lng], { icon: customIcon })
                .addTo(this.map)
                .bindPopup(popupContent);
            this.markers.push(marker);
        });

        window.odoo_open_face = (faceId) => {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'media.face',
                res_id: faceId,
                views: [[false, 'form']],
                target: 'current',
            });
        };

        window.odoo_open_site_from_face = async (siteId, category) => {
            let resModel = 'media.site';
            let resId = siteId;

            if (category === 'canopy') resModel = 'media.canopy';
            else if (category === 'billboard') resModel = 'media.billboard';
            else if (category === 'digital') resModel = 'media.digital.screen';

            if (resModel !== 'media.site') {
                const children = await this.orm.search(resModel, [['site_id', '=', siteId]], { limit: 1 });
                if (children.length > 0) {
                    resId = children[0];
                }
            }

            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: resModel,
                res_id: resId,
                views: [[false, 'form']],
                target: 'current',
            });
        };
    }
}

FaceMap.template = "media_inventory.FaceMap";
FaceMap.components = { Layout };

// Register the action
registry.category("actions").add("media_inventory.face_map_action", FaceMap);
