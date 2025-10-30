build_example(
  NAME current-working-file
  SOURCE_FILES current_working_file.cc
  LIBRARIES_TO_LINK
    ${libinternet}
    ${libwifi}
    ${libmesh}
    ${libcsma}
    ${libpoint-to-point}
    ${libapplications}
    ${libbuildings}
    ${libmobility}
    ${libnetanim}
    ${libflow-monitor}
)
