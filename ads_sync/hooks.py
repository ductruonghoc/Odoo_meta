# -*- coding: utf-8 -*-
from . import models


def post_init_hook(cr, registry):
    """Update menu active status after module installation."""
    env = registry.env(cr)
    env['ads.subscription']._update_menu_active()