build_example(
  NAME wifi-test-2-adhoc-grid
  SOURCE_FILES wifi-test-2-adhoc-grid.cc
  LIBRARIES_TO_LINK
    ${libinternet}
    ${libwifi}
    ${libmesh}
    ${libapplications}
    ${libnetanim}
    ${libflow-monitor}
    ${libbuildings}
    ${libcsma}
)

build_example(
  NAME wifi-test-2-adhoc-grid-six
  SOURCE_FILES six_node_layout/wifi-test-2-adhoc-grid-six.cc
  LIBRARIES_TO_LINK
    ${libinternet}
    ${libwifi}
    ${libmesh}
    ${libapplications}
    ${libnetanim}
    ${libflow-monitor}
    ${libbuildings}
    ${libcsma}
)

build_example(
  NAME wifi-test-2-adhoc-grid-six-hotspot-5g
  SOURCE_FILES six_node_layout/wifi-test-2-adhoc-grid-six-hotspot-5g.cc
  LIBRARIES_TO_LINK
    ${libinternet}
    ${libwifi}
    ${libmesh}
    ${libapplications}
    ${libnetanim}
    ${libflow-monitor}
    ${libbuildings}
    ${libcsma}
)

