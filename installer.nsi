!define PRODUCT_NAME "AutoOrtho"
;!define PRODUCT_VERSION "0.5.1"
;!define PY_VERSION "3.10.6"
;!define PY_MAJOR_VERSION "3.10"
;!define BITNESS "32"
!define ARCH_TAG ""
;!define INSTALLER_NAME "AutoOrtho_0.5.1.exe"
!define INSTALLER_NAME "AutoOrtho.exe"
!define PRODUCT_ICON "ao-icon.ico"

; Marker file to tell the uninstaller that it's a user installation
!define USER_INSTALL_MARKER _user_install_marker

SetCompressor lzma

!if "${NSIS_PACKEDVERSION}" >= 0x03000000
  Unicode true
  ManifestDPIAware true
!endif

!define MULTIUSER_EXECUTIONLEVEL Highest
!define MULTIUSER_INSTALLMODE_DEFAULT_CURRENTUSER
!define MULTIUSER_MUI
!define MULTIUSER_INSTALLMODE_COMMANDLINE
!define MULTIUSER_INSTALLMODE_INSTDIR "AutoOrtho"
!include MultiUser.nsh
!include FileFunc.nsh

; Modern UI installer stuff
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "ao-icon.ico"
!define MUI_UNICON "ao-icon.ico"

; UI pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MULTIUSER_PAGE_INSTALLMODE
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${INSTALLER_NAME}"
ShowInstDetails show

Var cmdLineInstallDir

Section -SETTINGS
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
SectionEnd


Section "!${PRODUCT_NAME}" sec_app
  SetRegView 32
  SectionIn RO
  File ${PRODUCT_ICON}

    ; Copy pkgs data
    ; SetOutPath "$INSTDIR\pkgs"
    ; File /r "pkgs\*.*"

  SetOutPath "$INSTDIR"

  ; Marker file for per-user install
  StrCmp $MultiUser.InstallMode CurrentUser 0 +3
    FileOpen $0 "$INSTDIR\${USER_INSTALL_MARKER}" w
    FileClose $0
    SetFileAttributes "$INSTDIR\${USER_INSTALL_MARKER}" HIDDEN

      ; Install files
  ;  SetOutPath "$INSTDIR"
  ;    File "ao-icon.ico"
  ;    File "AutoOrtho.launch.pyw"

  ; Install directories
  ;  SetOutPath "$INSTDIR\Python"
  ;  File /r "Python\*.*"
  ;  SetOutPath "$INSTDIR\templates"
  ;  File /r "templates\*.*"
  ;  SetOutPath "$INSTDIR\windows"
  ;  File /r "windows\*.*"
  ;  SetOutPath "$INSTDIR\aoimage"
  ;  File /r "aoimage\*.*"
  ;  SetOutPath "$INSTDIR\imgs"
  ;  File /r "imgs\*.*"
   SetOutPath "$INSTDIR"
   File /r "__main__.dist\*.*"
  ; File /r "autoortho_release\*.*"


  ; Install shortcuts
  ; The output path becomes the working directory for shortcuts
  SetOutPath "%HOMEDRIVE%\%HOMEPATH%"
    CreateShortCut "$SMPROGRAMS\AutoOrtho.lnk" "$INSTDIR\autoortho_win.exe" "$INSTDIR\ao-icon.ico"
  ;  CreateShortCut "$SMPROGRAMS\AutoOrtho.lnk" "$INSTDIR\Python\pythonw.exe" \
  ;    '"$INSTDIR\AutoOrtho.launch.pyw"' "$INSTDIR\ao-icon.ico"
  SetOutPath "$INSTDIR"


  ; Byte-compile Python files.
  ;DetailPrint "Byte-compiling Python modules..."
  ;nsExec::ExecToLog '"$INSTDIR\Python\python" -m compileall -q "$INSTDIR\pkgs"'
  WriteUninstaller $INSTDIR\uninstall.exe
  ; Add ourselves to Add/remove programs
  WriteRegStr SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "InstallLocation" "$INSTDIR"
  WriteRegStr SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayIcon" "$INSTDIR\${PRODUCT_ICON}"
  WriteRegStr SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegDWORD SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoModify" 1
  WriteRegDWORD SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoRepair" 1

  ; Check if we need to reboot
  IfRebootFlag 0 noreboot
    MessageBox MB_YESNO "A reboot is required to finish the installation. Do you wish to reboot now?" \
                /SD IDNO IDNO noreboot
      Reboot
  noreboot:
SectionEnd

Section "Uninstall"
  SetRegView 32
  SetShellVarContext all
  IfFileExists "$INSTDIR\${USER_INSTALL_MARKER}" 0 +3
    SetShellVarContext current
    Delete "$INSTDIR\${USER_INSTALL_MARKER}"

  Delete $INSTDIR\uninstall.exe
  Delete "$INSTDIR\${PRODUCT_ICON}"
  ;RMDir /r "$INSTDIR\pkgs"

  ; Remove ourselves from %PATH%

  ; Uninstall files
  ;  Delete "$INSTDIR\ao-icon.ico"
  ;  Delete "$INSTDIR\AutoOrtho.launch.pyw"
  ; Uninstall directories
  ;  RMDir /r "$INSTDIR\Python"
  ;  RMDir /r "$INSTDIR\templates"
  ;  RMDir /r "$INSTDIR\windows"
  ;  RMDir /r "$INSTDIR\aoimage"
  ;  RMDir /r "$INSTDIR\imgs"

  ; Uninstall shortcuts
      Delete "$SMPROGRAMS\AutoOrtho.lnk"
  RMDir /r $INSTDIR
  DeleteRegKey SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd


; Functions

Function .onMouseOverSection
    ; Find which section the mouse is over, and set the corresponding description.
    FindWindow $R0 "#32770" "" $HWNDPARENT
    GetDlgItem $R0 $R0 1043 ; description item (must be added to the UI)

    StrCmp $0 ${sec_app} "" +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:${PRODUCT_NAME}"

FunctionEnd

Function .onInit
  ; Multiuser.nsh breaks /D command line parameter. Parse /INSTDIR instead.
  ; Cribbing from https://nsis-dev.github.io/NSIS-Forums/html/t-299280.html
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} '$0' "/INSTDIR=" $1
  IfErrors +2  ; Error means flag not found
    StrCpy $cmdLineInstallDir $1
  ClearErrors
  
  ;Exec $INSTDIR\uninstall.exe 
  ;RMDir /r $INSTDIR

  ;  ${If} ${Silent}
  ;      ReadRegStr $R0 HKLM "${PROJECT_REG_UNINSTALL_KEY}" "QuietUninstallString"
  ;  ${Else}
  ;      ReadRegStr $R0 HKLM "${PROJECT_REG_UNINSTALL_KEY}" "UninstallString"
  ;  ${EndIf}
  ;  ExecWait "$R0"
  
  ReadRegStr $R0 SHCTX "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "UninstallString"
  ;ReadRegStr $R0 HKLM "${PROJECT_REG_UNINSTALL_KEY}" "UninstallString"
  ExecWait "$R0"

  !insertmacro MULTIUSER_INIT

  ; If cmd line included /INSTDIR, override the install dir set by MultiUser
  StrCmp $cmdLineInstallDir "" +2
    StrCpy $INSTDIR $cmdLineInstallDir
FunctionEnd

Function un.onInit
  !insertmacro MULTIUSER_UNINIT
FunctionEnd