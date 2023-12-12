set -o errexit
set -o xtrace
export USER=build
export HOME=/mnt
export DEBFULLNAME='%placeholder%'
export DEBEMAIL='%placeholder%'
mkdir -p /mnt/build && cd /mnt/build
tar xf compute-*[.tar.gz]
cd compute-*[^.tar.gz]
sed -e "s%\.\./\.\.%$PWD%" -i ../docs/source/conf.py
dh_make --copyright gpl3 --yes --python --file ../compute-*[.tar.gz]
rm debian/*.ex debian/README.{Debian,source} debian/*.docs
sed -e 's/\* Initial release.*/\* This is the development build, see commits in upstream repo for info./' -i debian/changelog
cp -v ../../files/{control,rules,copyright,docs,compute.bash-completion,install} debian/
dpkg-buildpackage -us -uc
