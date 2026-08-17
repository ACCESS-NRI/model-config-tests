"""Test expected output and expected data for test_test_config tests."""

expected_fullpaths = [
    # Top-level input
    "/g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/JRA55_MOM1_conserve2nd.nc",
    # Atmosphere submodel input
    "/g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/rmp_jrar_to_cict_CONSERV.nc",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data",
    # Ocean submodel input
    "/g/data/vk83/configurations/inputs/access-om2/ocean/grids/vertical/global.1deg/2020.10.22/ocean_vgrid.nc",
    "/g/data/vk83/configurations/inputs/access-om2/ocean/processor_masks/global.1deg/216.16x15/2020.05.30/ocean_mask_table",
    # Ice submodel input
    "/g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/grid.nc",
    "/g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/kmt.nc",
]

expected_hashes_from_repo = {
    # OM2 remapping_weights
    "/g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/JRA55_MOM1_conserve2nd.nc": "00be8ec0f1126055b65dc68178ce4eb5",
    "/g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/rmp_jrar_to_cict_CONSERV.nc": "10f0b5ea6b8102a03ad1140e5163a0f7",
    # JRA-55/RYF/v1-4/data directory
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.friver.1990_1991.nc": "fa3a55aeb6706a1b422d096f61a772c1",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.huss.1990_1991.nc": "6032d514fdfdd2b6a84bdef0a4ac3afe",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.licalvf.1990_1991.nc": "6f927702cbc023cc20d3ddd69695f0a0",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.prra.1990_1991.nc": "ac199086106ec4e41506e6082bccb109",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.prsn.1990_1991.nc": "cd076c877c2c5df61615e04d71ed00e0",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.psl.1990_1991.nc": "0dfd94a5c3234fd2016dfdd01e84a170",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rhuss.1990_1991.nc": "632519955305cb5c19e286b151439fb5",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rlds.1990_1991.nc": "0ea83e107ec883c3f39a12b60ff50d8e",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rsds.1990_1991.nc": "b74bf123f1e4557368a61732cf24f1c2",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.tas.1990_1991.nc": "06689885f4f2f726b95a2818ab78a20d",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.uas.1990_1991.nc": "107bf9480f55597655d2d283b6f6b4ff",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.vas.1990_1991.nc": "88dc8c70338bbc8f5efc48ed0009a99f",
    # OM2 ocean
    "/g/data/vk83/configurations/inputs/access-om2/ocean/grids/vertical/global.1deg/2020.10.22/ocean_vgrid.nc": "339ff716e3019a86fc861498e674250a",
    "/g/data/vk83/configurations/inputs/access-om2/ocean/processor_masks/global.1deg/216.16x15/2020.05.30/ocean_mask_table": "2203b38758fb2b56a145ef16b7872af9",
    # OM2 ice
    "/g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/grid.nc": "7dd9ee5bce7f2eaeb75355684ddba599",
    "/g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/kmt.nc": "9609d3db04f58cba200d7186dfe68ebd",
}

expected_local_hashes = {
    "/g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/JRA55_MOM1_conserve2nd.nc": "00be8ec0f1126055b65dc68178ce4eb5",
    "/g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/rmp_jrar_to_cict_CONSERV.nc": "10f0b5ea6b8102a03ad1140e5163a0f7",
    "/g/data/vk83/configurations/inputs/access-om2/ocean/grids/vertical/global.1deg/2020.10.22/ocean_vgrid.nc": "339ff716e3019a86fc861498e674250a",
    "/g/data/vk83/configurations/inputs/access-om2/ocean/processor_masks/global.1deg/216.16x15/2020.05.30/ocean_mask_table": "2203b38758fb2b56a145ef16b7872af9",
    "/g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/grid.nc": "7dd9ee5bce7f2eaeb75355684ddba599",
    "/g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/kmt.nc": "9609d3db04f58cba200d7186dfe68ebd",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.friver.1990_1991.nc": "fa3a55aeb6706a1b422d096f61a772c1",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.huss.1990_1991.nc": "6032d514fdfdd2b6a84bdef0a4ac3afe",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.licalvf.1990_1991.nc": "6f927702cbc023cc20d3ddd69695f0a0",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.prra.1990_1991.nc": "ac199086106ec4e41506e6082bccb109",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.prsn.1990_1991.nc": "cd076c877c2c5df61615e04d71ed00e0",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.psl.1990_1991.nc": "0dfd94a5c3234fd2016dfdd01e84a170",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rhuss.1990_1991.nc": "632519955305cb5c19e286b151439fb5",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rlds.1990_1991.nc": "0ea83e107ec883c3f39a12b60ff50d8e",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rsds.1990_1991.nc": "b74bf123f1e4557368a61732cf24f1c2",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.tas.1990_1991.nc": "06689885f4f2f726b95a2818ab78a20d",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.uas.1990_1991.nc": "107bf9480f55597655d2d283b6f6b4ff",
    "/g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.vas.1990_1991.nc": "88dc8c70338bbc8f5efc48ed0009a99f",
}
