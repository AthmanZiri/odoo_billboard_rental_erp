/** @odoo-module */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

const actionRegistry = registry.category("actions");

// Wait for the next tick to ensure PartnerLedger is registered if needed,
// but usually Odoo's module system handles dependencies correctly.
// Since partner_ledger_filter depends on dynamic_accounts_report, 
// the original script should have run already.

const PartnerLedger = actionRegistry.get("p_l");

if (PartnerLedger) {
    patch(PartnerLedger.prototype, {
        setup() {
            super.setup();
            this.partnerSources = [
                {
                    placeholder: "Search Partners...",
                    options: async (term) => {
                        const partners = await this.orm.call("res.partner", "name_search", [], {
                            name: term,
                            domain: [],
                            limit: 10,
                        });
                        return partners.map((partner) => {
                            const val = {
                                id: partner[0],
                                label: partner[1],
                                display_name: partner[1],
                            };
                            return {
                                ...val,
                                onSelect: () => this.onPartnerSelected(val),
                            };
                        });
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

    PartnerLedger.components = {
        ...(PartnerLedger.components || {}),
        AutoComplete,
    };
}
