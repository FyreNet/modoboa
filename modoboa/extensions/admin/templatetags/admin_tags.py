from django import template
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _, ugettext_lazy
from django.core.urlresolvers import reverse
from modoboa.lib import events
from modoboa.lib.webutils import render_actions
from modoboa.lib.templatetags.lib_tags import render_link

register = template.Library()

genders = {
    "Enabled": (ugettext_lazy("enabled_m"), ugettext_lazy("enabled_f"))
}


@register.simple_tag
def domains_menu(selection, user):
    """Specific menu for domain related operations.

    Corresponds to the menu visible on the left column when you go to
    Domains.

    :param str selection: menu entry currently selected
    :param ``User`` user: connected user
    :rtype: str
    :return: rendered menu (as HTML)
    """
    if not user.has_perm("admin.add_domain"):
        return ""

    entries = [
        {"name": "newdomain",
         "label": _("Add domain"),
         "img": "fa fa-plus",
         "modal": True,
         "modalcb": "admin.newdomain_cb",
         "url": reverse("admin:domain_add")},
    ]
    entries += events.raiseQueryEvent("ExtraDomainMenuEntries", user)
    entries += [
        {"name": "import",
         "label": _("Import"),
         "img": "fa fa-folder-open",
         "url": reverse("admin:domain_import"),
         "modal": True,
         "modalcb": "admin.importform_cb"},
        {"name": "export",
         "label": _("Export"),
         "img": "fa fa-share-alt",
         "url": reverse("admin:domain_export"),
         "modal": True,
         "modalcb": "admin.exportform_cb"}
    ]

    return render_to_string('common/menulist.html', {
        "entries": entries,
        "selection": selection,
        "user": user
    })


@register.simple_tag
def identities_menu(user, selection=None):
    """Menu specific to the Identities page.

    :param ``User`` user: the connecter user
    :rtype: str
    :return: the rendered menu
    """
    entries = [
        {"name": "identities",
         "label": _("List identities"),
         "img": "fa fa-user",
         "class": "ajaxlink navigation",
         "url": "list/"},
        {"name": "quotas",
         "label": _("List quotas"),
         "img": "fa fa-hdd-o",
         "class": "ajaxlink navigation",
         "url": "quotas/"},
        {"name": "newaccount",
         "label": _("Add account"),
         "img": "fa fa-plus",
         "modal": True,
         "modalcb": "admin.newaccount_cb",
         "url": reverse("admin:account_add")},
        {"name": "newalias",
         "label": _("Add alias"),
         "img": "fa fa-plus",
         "modal": True,
         "modalcb": "admin.aliasform_cb",
         "url": reverse("admin:alias_add")},
        {"name": "newforward",
         "label": _("Add forward"),
         "img": "fa fa-plus",
         "modal": True,
         "modalcb": "admin.aliasform_cb",
         "url": reverse("admin:forward_add")},
        {"name": "newdlist",
         "label": _("Add distribution list"),
         "img": "fa fa-plus",
         "modal": True,
         "modalcb": "admin.aliasform_cb",
         "url": reverse("admin:dlist_add")},
        {"name": "import",
         "label": _("Import"),
         "img": "fa fa-folder-open",
         "url": reverse("admin:identity_import"),
         "modal": True,
         "modalcb": "admin.importform_cb"},
        {"name": "export",
         "label": _("Export"),
         "img": "fa fa-share-alt",
         "url": reverse("admin:identity_export"),
         "modal": True,
         "modalcb": "admin.exportform_cb"
         }
    ]

    return render_to_string('common/menulist.html', {
        "entries": entries,
        "user": user,
        "selection": selection
    })


@register.simple_tag
def domain_actions(user, domain):
    actions = []
    if domain.__class__.__name__ == 'Domain':
        actions = [
            {"name": "listidentities",
             "url": reverse("admin:identity_list") + "#list/?searchquery=@%s" % domain.name,
             "title": _("View the domain's identities"),
             "img": "fa fa-user"}
        ]
        if user.has_perm("admin.delete_domain"):
            actions.append({
                "name": "deldomain",
                "url": reverse("admin:domain_delete", args=[domain.id]),
                "title": _("Delete %s?" % domain.name),
                "img": "fa fa-trash"
            })
    else:
        actions = events.raiseQueryEvent('GetDomainActions', user, domain)

    return render_actions(actions)


@register.simple_tag
def identity_actions(user, ident):
    name = ident.__class__.__name__
    objid = ident.id
    if name == "User":
        actions = events.raiseQueryEvent("ExtraAccountActions", ident)
        actions += [
            {"name": "delaccount",
             "url": reverse("admin:account_delete", args=[objid]),
             "img": "fa fa-trash",
             "title": _("Delete %s?" % ident.username)},
        ]
    else:
        actions = [
            {"name": "delalias",
             "url": reverse("admin:alias_delete") + "?selection=%s" % objid,
             "img": "fa fa-trash",
             "title": _("Delete %s?" % ident.full_address)},
        ]
    return render_actions(actions)


@register.simple_tag
def disable_identity(identity):
    """Disable an identity.

    Finding this information depends on the identity type.
    """
    if identity.__class__.__name__ == "User":
        if identity.is_active and identity.mailbox_set.count() \
           and identity.mailbox_set.all()[0].domain.enabled:
            return ""
    elif identity.enabled and identity.domain.enabled:
        return ""
    return "muted"

@register.simple_tag
def domain_modify_link(domain):
    linkdef = {"label": domain.name, "modal": True}
    if domain.__class__.__name__ == "Domain":
        linkdef["url"] = reverse("admin:domain_change", args=[domain.id])
        linkdef["modalcb"] = "admin.domainform_cb"
    else:
        tmp = events.raiseDictEvent('GetDomainModifyLink', domain)
        for key in ['url', 'modalcb']:
            linkdef[key] = tmp[key]
    return render_link(linkdef)


@register.simple_tag
def domain_aliases(domain):
    """Display domain aliases of this domain.

    :param domain:
    :rtype: str
    """
    if not domain.aliases.count():
        return '---'
    res = ''
    for alias in domain.aliases.all():
        res += '%s<br/>' % alias.name
    return res


@register.simple_tag
def identity_modify_link(identity, active_tab='default'):
    """Return the appropriate modification link.

    According to the identity type, a specific modification link (URL)
    must be used.

    :param identity: a ``User`` or ``Alias`` instance
    :param str active_tab: the tab to display
    :rtype: str
    """
    linkdef = {"label": identity.identity, "modal": True}
    if identity.__class__.__name__ == "User":
        linkdef["url"] = reverse("admin:account_change", args=[identity.id])
        linkdef["url"] += "?active_tab=%s" % active_tab
        linkdef["modalcb"] = "admin.editaccount_cb"
    else:
        linkdef["url"] = reverse("admin:alias_change", args=[identity.id])
        linkdef["modalcb"] = "admin.aliasform_cb"
    return render_link(linkdef)


@register.simple_tag
def domadmin_actions(daid, domid):
    actions = [{
        "name": "removeperm",
        "url": "{}?domid={}&daid={}".format(
            reverse("admin:permission_remove"), domid, daid),
        "img": "fa fa-trash",
        "title": _("Remove this permission")
    }]
    return render_actions(actions)


@register.filter
def gender(value, target):
    if value in genders:
        trans = target == "m" and genders[value][0] or genders[value][1]
        if trans.find("_") == -1:
            return trans
    return value


@register.simple_tag
def get_extra_admin_content(user, target, currentpage):
    res = events.raiseQueryEvent(
        "ExtraAdminContent", user, target, currentpage
    )
    return "".join(res)


