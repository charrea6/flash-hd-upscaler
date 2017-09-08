#!/usr/bin/env bash

BASE_DIR=expanded

#TEST=echo
TEST=

find ${BASE_DIR} | grep xml | grep LIBRARY | xargs ${TEST} rm

find ${BASE_DIR} | grep DOMDocument.xml | xargs ${TEST} rm
find ${BASE_DIR} | grep PublishSettings.xml | xargs ${TEST} rm
find ${BASE_DIR} | grep MobileSettings.xml | xargs ${TEST} rm

find ${BASE_DIR} | grep metadata.xml | xargs ${TEST} rm

find ${BASE_DIR} | grep xml

# --- Some files seem to have slipped through
#./advanced_scanning/LIBRARY/Zuruck copy.xml
#./mainmenu/LIBRARY/&#60main_menu&#62/&#60pvr_selection_list&#62/ArrowUpDown copy.xml
#./mainmenu/LIBRARY/&#60service_menu_list&#62/&#60service_menu_selection_list&#62/ArrowUpDown copy.xml
#./infobox/LIBRARY/&#60circular_list&#62/&#60circular_list&#62 copy 9/CircularListContainerMask.xml
#./infobox/LIBRARY/&#60circular_list&#62/&#60circular_list&#62 copy 9/CircularListItem.xml
#./infobox_v1_flash8/LIBRARY/&#60circular_list&#62/&#60circular_list&#62 copy 9/CircularListContainerMask.xml
#./infobox_v1_flash8/LIBRARY/&#60circular_list&#62/&#60circular_list&#62 copy 9/CircularListItem.xml
#./pvr_instant_recording/LIBRARY/&#60circular_list&#62/&#60circular_list&#62 copy 7/CircularListContainerMask.xml
#./pvr_instant_recording/LIBRARY/&#60circular_list&#62/&#60circular_list&#62 copy 7/CircularListItem.xml
