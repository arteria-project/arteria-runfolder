%define name runfolder
%define version 1.0.1
%define unmangled_version 1.0.1
%define unmangled_version 1.0.1
%define release 1
%global confdir %{_sysconfdir}/%{name}

Summary: Microservice for managing runfolders
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: UNKNOWN
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: SNP&SEQ Technology Platform, Uppsala University <UNKNOWN>

# Systemd files
Source1:          runfolder.service
Source2:          runfolder.socket
Source3:          runfolder.conf
Requires(post):   systemd-units
Requires(preun):  systemd-units
Requires(postun): systemd-units
BuildRequires:    systemd-units

%description
Arteria-Runfolder
=================

A self contained (Tornado) REST service for managing runfolders.

**Try it out:**

Install using pip:

    pip install -r requirements/dev . # possible add -e if you're in development mode.

Open up the `config/app.config` and specify the root directories that you want to monitor for runfolders. Then run:

    runfolder-ws --port 9999 --configroot config/

This will star the runfolder service on port 9999, and the api dock will be available under `localhost:9999/api`.
Try curl-ing to see what you can do with it:

    curl localhost:9999/api

**Running the tests**
After install you could run the integration tests to see if everything works as expected:
    ./runfolder_tests/run_integration_tests.py

This will by default start a local server, run the integration tests on it and then shut the server down.

Alternatively, you can run the same script against a remote server, specifying the URL and the runfolder directory:
    ./runfolder_tests/run_integration_tests.py http://testarteria1:10800/api/1.0 /data/testartera1/runfolders

Unit tests can be run with
    nosetests ./runfolder_tests/unit

**Install in production**
One way to install this as a daemon in a production environment
can be seen at https://github.com/arteria-project/arteria-provisioning


%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
install -d -m 755 $RPM_BUILD_ROOT%{confdir}
install -d -m 755 $RPM_BUILD_ROOT%{_unitdir}
pushd .
  # Install systemd files
  install -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_unitdir}/%{name}.service
  install -m 644 %{SOURCE2} $RPM_BUILD_ROOT%{_unitdir}/%{name}.socket
  install -m 644 %{SOURCE3} $RPM_BUILD_ROOT%{confdir}/%{name}.conf
popd

%pre
# Add runfolder user and group
getent group %{name} >/dev/null || groupadd -f -r %{name}
getent passwd %{name} >/dev/null || useradd -r -m -g %{name} -s /sbin/nologin -c "The Runfolder user" %{name}
exit 0

%post
%systemd_post %{name}.service
%systemd_post %{name}.socket

%preun
%systemd_preun %{name}.service
%systemd_preun %{name}.socket

%postun
%systemd_postun_with_restart %{name}.service
%systemd_postun_with_restart %{name}.socket

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%config(noreplace) %{confdir}/%{name}.conf
%{_unitdir}/%{name}.service
%{_unitdir}/%{name}.socket
