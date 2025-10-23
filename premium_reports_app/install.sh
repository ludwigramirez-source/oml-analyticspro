#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color
ADDON_NAME='premium_reports_app'
ADDON_STRING="PremiumReports"

Install() {
  OML_PATH="/opt/omnileads/ominicontacto"
  OML_BIN_PATH="/opt/omnileads/bin"
  mkdir -p $OML_PATH/$ADDON_NAME
  echo "** [$ADDON_NAME] Checking OmniLeads version"
  oml_version=`cat ${OML_PATH}/ominicontacto_app/version.py |grep OML_BRANCH |awk -F "=" '{gsub(/"/, "", $2); print $2}'`
  if [[ ${oml_version} == *"release-1.2"* ]] || [[ ${oml_version} == *"release-1.3"* ]]; then
    echo "** OMniLeads version not supported to install this addon, please first upgrade your instance"
    exit 1
  fi
  content="`cat $OML_PATH/../bin/addons_installed.sh`"
   if [[ $content != *"$ADDON_NAME"* ]]; then
     echo "** [$ADDON_NAME] Modifying variable ADDONS_INSTALLED"
     echo "ADDONS_INSTALLED+=('$ADDON_NAME')" >> ${OML_PATH}/../bin/addons_installed.sh
     chown -R omnileads. ${OML_PATH}/../bin/addons_installed.sh
  fi
  echo "** [$ADDON_NAME] Copying the $ADDON_NAME folder to ${OML_PATH}"
  release=$(ls -d */ | grep -v docs|rev|cut -c 2-|rev)
  rm -rf ${OML_PATH}/${ADDON_NAME}
  if [ ! -d ${OML_PATH}/${ADDON_NAME} ];
    then mkdir ${OML_PATH}/${ADDON_NAME};
  fi
  cp -a ${release}/* ${OML_PATH}/${ADDON_NAME}
  source /etc/profile.d/omnileads_envars.sh
  if [ -z $PREMIUM_REPORTS_VERSION ]; then
    echo "** [$ADDON_NAME] Adding the $ADDON_NAME version to omnileads_envars.sh"
    sed -i "/^export.*/i PREMIUM_REPORTS_VERSION=$release" /etc/profile.d/omnileads_envars.sh
    sed -i '$s/$/ PREMIUM_REPORTS_VERSION/' /etc/profile.d/omnileads_envars.sh
  else
    sed -i "s/^PREMIUM_REPORTS_VERSION.*/PREMIUM_REPORTS_VERSION=$release/g" /etc/profile.d/omnileads_envars.sh
  fi
  content="`cat $OML_PATH/ominicontacto/settings/addons.py`"
  if [[ $content != *"$ADDON_NAME"* ]]; then
    echo "** [$ADDON_NAME] Editing settings file addons.py" && \
    echo "ADDONS_APPS += ['$ADDON_NAME.apps.PremiumReportsAppConfig',]" >> ${OML_PATH}/ominicontacto/settings/addons.py && \
    echo "ADDON_URLPATTERNS +=[ (r'^', '$ADDON_NAME.urls'), ]" >> ${OML_PATH}/ominicontacto/settings/addons.py && \
    echo "ADDONS_LOCALE_PATHS += (os.path.join(BASE_DIR, '$ADDON_NAME/locale'), )" >> ${OML_PATH}/ominicontacto/settings/addons.py
  else
    sed -i "s/.*${ADDON_NAME}.apps.*/ADDONS_APPS += ['${ADDON_NAME}.apps.${ADDON_STRING}AppConfig',]/" ${OML_PATH}/ominicontacto/settings/addons.py \
    &&  sed -i "s/.*${ADDON_NAME}.urls.*/ADDON_URLPATTERNS += [ (r'^', '${ADDON_NAME}.urls'), ]/" ${OML_PATH}/ominicontacto/settings/addons.py \
    && sed -i "s/.*${ADDON_NAME}\/locale.*/ADDONS_LOCALE_PATHS = (os.path.join(BASE_DIR, '$ADDON_NAME\/locale'), )/" ${OML_PATH}/ominicontacto/settings/addons.py
  fi
  echo "** [$ADDON_NAME] Executing django commands"
  $OML_BIN_PATH/manage.sh collectstatic --noinput
  $OML_BIN_PATH/manage.sh collectstatic_js_reverse
  $OML_BIN_PATH/manage.sh compress --force
  $OML_BIN_PATH/manage.sh actualizar_permisos
  $OML_BIN_PATH/manage.sh compilemessages
  ResultadoInstall=`echo $?`
  chown -R omnileads. $OML_PATH/../static
  chown -R omnileads. $OML_PATH
  if [ $ResultadoInstall == 0 ]; then
    printf "$GREEN** [$ADDON_NAME] Premium Reports Addon installed successfully $NC\n"
    printf "$GREEN**  Don't forget to restart your omnileads service: $NC\n"
    printf "$GREEN**    - service omnileads restart for AIO servers $NC\n"
    printf "$GREEN**    - docker restart oml-omniapp-prodenv for docker prodenv $NC\n"
  else
    printf "$RED** [$ADDON_NAME] There was an error during installation, contact your administrator if you can't fix it $NC\n"
  fi
}
Install
