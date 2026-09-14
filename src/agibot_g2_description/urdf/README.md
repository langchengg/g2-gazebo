# Generated robot description

The complete URDF and mesh assets are generated outside source control by
`scripts/convert_g2_model.py`. The default container location is
`/opt/g2-model/g2.urdf`; the runtime must mount the complete, checked generated
directory at `/opt/g2-model` read-only or copy it into a private local image.

The original AgiBot World assets and derived meshes retain CC BY-NC-SA 4.0.
The package license applies to project-owned wrappers only. It does not
relicense the generated model. No proprietary GitHub G2 meshes are used.
