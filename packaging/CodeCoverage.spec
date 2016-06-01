Name:          CodeCoverage
Version:       %{version}
Release:       1%{?dist}
Summary:       A wrapper for building and running code coverage on NetMon C++ repositories
Group:         Development/Tools
License:       MIT
BuildRequires: probecmake >= 2.8
ExclusiveArch: x86_64

%description

%prep
cd ~/rpmbuild/BUILD
rm -rf %{name}
mkdir -p %{name}
cd %{name}
tar xzf ~/rpmbuild/SOURCES/%{name}-%{version}.tar.gz
if [ $? -ne 0 ]; then
   exit $?
fi

%build
cd %{name}
mkdir -p $RPM_BUILD_ROOT/usr/local/probe/bin
cp scripts/CodeCoverage.py $RPM_BUILD_ROOT/usr/local/probe/bin/CodeCoverage.py

%post

%preun

%postun

%files
%defattr(-,dpi,dpi,-)
/usr/local/probe/bin
