@ECHO OFF
pushd %~dp0

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=source
set BUILDDIR=build
if "%SPHINXOPTS%" == "" (
	set SPHINXOPTS=-W --keep-going
)

if "%1" == "" goto help

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo The 'sphinx-build' command was not found. Install Sphinx, then retry.
	exit /b 1
)

if /I "%1" == "html" (
	python "%~dp0scripts\check_api_examples.py"
	if errorlevel 1 (
		popd
		exit /b 1
	)
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%

:end
popd
