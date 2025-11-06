build_example(
  NAME wifi-test1-adhoc-grid
  SOURCE_FILES wifi-test1-adhoc-grid.cc
  LIBRARIES_TO_LINK
    ${libinternet}
    ${libwifi}
    ${libolsr}
    ${libnetanim}
    ${libflow-monitor}
)

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

