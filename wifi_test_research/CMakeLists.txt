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


