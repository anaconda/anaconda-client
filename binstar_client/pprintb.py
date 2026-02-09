from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated
from binstar_client.commands.groups import package_list, user_list


deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="package_list",
    value=package_list,
    addendum="Use `binstar_client.commands.groups.package_list` instead",
)
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="user_list",
    value=user_list,
    addendum="Use `binstar_client.commands.groups.user_list` instead",
)

del DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated
