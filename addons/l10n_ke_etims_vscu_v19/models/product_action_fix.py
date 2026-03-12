    def action_l10n_ke_oscu_save_item(self):
        """ Register a product with eTIMS (user action).

        Regstration allows the product to be used via its itemCd in other requests such as invoice
        and stock move reporting.
        """
        validation_messages = self._l10n_ke_get_validation_messages(for_invoice=False)
        for message in validation_messages.values():
            if message.get('blocking'):
                raise UserError(_(\"Cannot register '%(name)s' on eTIMS:\\n%(msg)s\", name=self.name, msg=message['message']))
        error, _content = self._l10n_ke_oscu_save_item()
        if error:
            raise UserError(f\"[{error['code']}] {error['message']}\")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _(\"Product successfully registered\"),
                'next': {'type': 'ir.actions.act_window', 'res_model': 'product.product', 'res_id': self.id, 'views': [[False, 'form']]},
            }
        }
