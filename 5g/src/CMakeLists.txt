# CMakeLists.txt for 5G NR simulations

# Get all .cc files in this directory
file(GLOB 5G_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/[^.]*.cc)

# Build each .cc file as a separate executable
foreach(source_file ${5G_SOURCES})
  get_filename_component(exec_name ${source_file} NAME_WLE)
  
  build_exec(
    EXECNAME ${exec_name}
    EXECNAME_PREFIX 5g_
    SOURCE_FILES "${source_file}"
    LIBRARIES_TO_LINK "${ns3-libs}" "${ns3-contrib-libs}"
    EXECUTABLE_DIRECTORY_PATH ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/5g/
  )
endforeach()

