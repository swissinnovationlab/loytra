from loytra_modules import LoytraModuleInstance, Moduler

__loytra_module__ = LoytraModuleInstance(
    module_name="loytra",
    moduler=Moduler(package="loytra_cli",
                    module="loytra_cli",
                    hash="main",
                    url="github.com/swissinnovationlab/loytra"),
    sort_index=0
)

