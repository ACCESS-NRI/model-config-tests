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

# Mock requests.get responses for manifest files from model-config-inputs, mapping URLs to their expected content
mock_input_response = {
    "https://raw.githubusercontent.com/ACCESS-NRI/model-config-inputs/main/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/.manifest.yaml": """format: yamanifest
version: 1.0
---
JRA55_MOM1_conserve2nd.nc:
  fullpath: /g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/JRA55_MOM1_conserve2nd.nc
  hashes:
    binhash: 3ba86d1ae2c7641a29dce1179c55ad64
    md5: 00be8ec0f1126055b65dc68178ce4eb5
rmp_jrar_to_cict_CONSERV.nc:
  fullpath: /g/data/vk83/configurations/inputs/access-om2/remapping_weights/JRA55/global.1deg/2020.05.30/rmp_jrar_to_cict_CONSERV.nc
  hashes:
    binhash: 1408c9a906c2c24a5a4cbdd47cd41670
    md5: 10f0b5ea6b8102a03ad1140e5163a0f7""",
    "https://raw.githubusercontent.com/ACCESS-NRI/model-config-inputs/main/JRA-55/RYF/v1-4/data/.manifest.yaml": """format: yamanifest
version: 1.0
---
RYF.friver.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.friver.1990_1991.nc
  hashes:
    binhash: abba207de30541a83d25e24b424cfa87
    md5: fa3a55aeb6706a1b422d096f61a772c1
RYF.huss.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.huss.1990_1991.nc
  hashes:
    binhash: 1d67d219c6f161051dec204a1842a968
    md5: 6032d514fdfdd2b6a84bdef0a4ac3afe
RYF.licalvf.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.licalvf.1990_1991.nc
  hashes:
    binhash: 834da0a081e904fdbc892255d1954062
    md5: 6f927702cbc023cc20d3ddd69695f0a0
RYF.prra.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.prra.1990_1991.nc
  hashes:
    binhash: 7bc006b83a9891d4f9ef39f4d94ffb05
    md5: ac199086106ec4e41506e6082bccb109
RYF.prsn.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.prsn.1990_1991.nc
  hashes:
    binhash: a57a154152a830ad1ca820ca9487d5ac
    md5: cd076c877c2c5df61615e04d71ed00e0
RYF.psl.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.psl.1990_1991.nc
  hashes:
    binhash: 420c371361bb677eb87c01255c6e62b3
    md5: 0dfd94a5c3234fd2016dfdd01e84a170
RYF.rhuss.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rhuss.1990_1991.nc
  hashes:
    binhash: fe4460b8d68f94df26adc52fb56a0d6a
    md5: 632519955305cb5c19e286b151439fb5
RYF.rlds.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rlds.1990_1991.nc
  hashes:
    binhash: 07a7fb6f9d2a3aee4081034f0cfc305a
    md5: 0ea83e107ec883c3f39a12b60ff50d8e
RYF.rsds.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.rsds.1990_1991.nc
  hashes:
    binhash: 2d6c41b66024e460fcfe0a1668bfe151
    md5: b74bf123f1e4557368a61732cf24f1c2
RYF.tas.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.tas.1990_1991.nc
  hashes:
    binhash: 2a7a2f9903346123161b91ed8d5fab52
    md5: 06689885f4f2f726b95a2818ab78a20d
RYF.uas.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.uas.1990_1991.nc
  hashes:
    binhash: bfd4876aac0b31e51a18c7724c84d8b1
    md5: 107bf9480f55597655d2d283b6f6b4ff
RYF.vas.1990_1991.nc:
  fullpath: /g/data/vk83/configurations/inputs/JRA-55/RYF/v1-4/data/RYF.vas.1990_1991.nc
  hashes:
    binhash: d15ca562e37e82fb2d31657701f0a560
    md5: 88dc8c70338bbc8f5efc48ed0009a99f""",
    "https://raw.githubusercontent.com/ACCESS-NRI/model-config-inputs/main/access-om2/ocean/grids/vertical/global.1deg/2020.10.22/.manifest.yaml": """format: yamanifest
version: 1.0
---
ocean_vgrid.nc:
  fullpath: /g/data/vk83/configurations/inputs/access-om2/ocean/grids/vertical/global.1deg/2020.10.22/ocean_vgrid.nc
  hashes:
    binhash: 4fd591112647a35b9450058070ce92ad
    md5: 339ff716e3019a86fc861498e674250a""",
    "https://raw.githubusercontent.com/ACCESS-NRI/model-config-inputs/main/access-om2/ocean/processor_masks/global.1deg/216.16x15/2020.05.30/.manifest.yaml": """format: yamanifest
version: 1.0
---
ocean_mask_table:
  fullpath: /g/data/vk83/configurations/inputs/access-om2/ocean/processor_masks/global.1deg/216.16x15/2020.05.30/ocean_mask_table
  hashes:
    binhash: f92a6c9cd60eb7ecae2c822031fc6dbe
    md5: 2203b38758fb2b56a145ef16b7872af9""",
    "https://raw.githubusercontent.com/ACCESS-NRI/model-config-inputs/main/access-om2/ice/grids/global.1deg/2024.04.17/.manifest.yaml": """format: yamanifest
version: 1.0
---
grid.nc:
  fullpath: /g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/grid.nc
  hashes:
    binhash: 8af00ee2b12207979097bf67708b38e5
    md5: 7dd9ee5bce7f2eaeb75355684ddba599
kmt.nc:
  fullpath: /g/data/vk83/configurations/inputs/access-om2/ice/grids/global.1deg/2024.04.17/kmt.nc
  hashes:
    binhash: 5b1a8f815221fe504a70e7b7183ea995
    md5: 9609d3db04f58cba200d7186dfe68ebd""",
}
