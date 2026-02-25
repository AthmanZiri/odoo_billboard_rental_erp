/** @odoo-module */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { Autocomplete } from "@web/core/autocomplete/autocomplete";

const actionRegistry = registry.category("actions");

// Wait for the next tick to ensure PartnerLedger is registered if needed,
// but usually Odoo's module system handles dependencies correctly.
// Since partner_ledger_filter depends on dynamic_accounts_report, 
// the original script should have run already.

const PartnerLedger = actionRegistry.get("p_l");

if (PartnerLedger) {
    patch(PartnerLedger.prototype, "partner_ledger_filter.PartnerLedger", {
        setup() {
            this._super(...arguments);
            this.partnerSources = [
                {
                    placeholder: "Search Partners...",
                    search: async (term) => {
                        const partners = await this.orm.call("res.partner", "name_search", [], {
                            name: term,
                            args: [],
                            limit: 10,
                        });
                        return partners.map((partner) => ({
                            id: partner[0],
                            display_name: partner[1],
                        }));
                    },
                },
            ];
        },
        async onPartnerSelected(val) {
            // Apply filter using the same logic as the original component
            // val is {id: ..., display_name: ...}
            await this.applyFilter([val], {
                input: {
                    attributes: {
                        placeholder: {
                            value: 'Partner'
                        }
                    }
                }
            });
        }
    });

    // Add Autocomplete to components
    PartnerLedger.components = {
        ...PartnerLedger.components,
        Autocomplete,
    };
}
