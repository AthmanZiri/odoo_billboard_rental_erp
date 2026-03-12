-- neutralize connection to eTIMS VSCU
UPDATE res_company
SET l10n_ke_oscu_cmc_key = '', l10n_ke_server_mode='test';
