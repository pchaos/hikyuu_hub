#!/usr/bin/python
# -*- coding: utf8 -*-
#
# Create on: 2024-01-24
#    Author: fasiondog

import os
import sys
import shutil
import subprocess
import datetime
import click
import hikyuu

HIKYUU_DIR = os.path.dirname(os.path.abspath(hikyuu.__file__))
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

lib_dir = f"{HIKYUU_DIR}/cpp"
include_dir = f"{HIKYUU_DIR}/include"
if not os.path.lexists(f"{HIKYUU_DIR}/include"):
    include_dir = "{}/hikyuu_cpp".format(
        os.path.dirname(os.path.abspath(HIKYUU_DIR)))
lib_dir = lib_dir.replace('\\', "\\\\")
include_dir = include_dir.replace('\\', "\\\\")

today = datetime.date.today()
username = os.getlogin()

xmake_template = """
add_rules("mode.debug", "mode.release")
set_languages("cxx17")

if is_plat("windows") then
    if is_mode("release") then
        set_runtimes("MD")
    else
        set_runtimes("MDd")
    end
end

add_repositories("hikyuu-repo https://github.com/fasiondog/hikyuu_extern_libs.git")
add_requires("pybind11", {{system = false}})

add_requires("pybind11", {{system = false}})
add_requires("boost", {{
  system = false,
  debug = is_mode("debug"),  
  configs = {{
    shared = false,
    multi = true,
    date_time = true,
    filesystem = true,
    serialization = true,
    system = false,
    python = false,
  }},
}})

add_requires("spdlog", {{system = false, configs = {{header_only = true, fmt_external = true}}}})
add_requireconfs("spdlog.fmt", {{override = true, version = fmt_version, configs = {{header_only = true}}}})

target("export")
    set_kind("shared")
    if is_plat("windows") then
        set_extension(".pyd")
    else 
        set_filename("export.so")
    end

    add_packages("pybind11", "boost", "fmt", "spdlog")

    add_includedirs("{include_dir}")
    add_linkdirs("{lib_dir}")

    add_links("hikyuu")
    add_files("**.cpp")

    if is_plat("windows") then
        add_cxflags("-EHsc", "/Zc:__cplusplus", "/utf-8")
    end

    on_load("windows", "linux", "macosx", function(target)
        import("lib.detect.find_tool")
        if is_plat("windows") then
            -- detect installed python3
            local python = assert(find_tool("python", {{version = true}}), "python not found, please install it first! note: python version must > 3.0")
            assert(python.version > "3", python.version .. " python version must > 3.0, please use python3.0 or later!")
            -- find python include and libs directory
            local pydir = os.iorun("python -c 'import sys; print(sys.executable)'")
            pydir = path.directory(pydir)
            target:add("includedirs", pydir .. "/include")
            target:add("linkdirs", pydir .. "/libs")
            return
        end
    
        -- get python include directory.
        local pydir = nil;
        if os.getenv("CONDA_PREFIX") ~= nil then
            local py3config = os.getenv("CONDA_PREFIX") .. "/bin/python3-config"
            pydir = try {{ function () return os.iorun(py3config .. " --includes"):trim() end }}
        else
            pydir = try {{ function () return os.iorun("python3-config --includes"):trim() end }}
        end
        assert(pydir, "python3-config not found!")
        target:add("cxflags", pydir)   
    end)
    
    after_build(function(target)
        local dst_dir = "./"
        local dst_obj = dst_dir .. "core.so"
        if not is_plat("cross") then
            import("lib.detect.find_tool")
            local python = assert(find_tool("python", {{version = true}}), "python not found, please install it first! note: python version must > 3.0")
            local tmp = string.split(python.version, "%.")
            dst_obj = dst_dir .. "export" .. tmp[1] .. tmp[2]
        end

        if is_plat("windows") then
            os.cp(target:targetdir() .. '/export.pyd', dst_obj .. ".pyd")
        elseif is_plat("macosx") then
            os.cp(target:targetdir() .. '/export.so', dst_obj .. ".so")
        else
            if not is_plat("cross") then
                os.trycp(target:targetdir() .. '/*.so', dst_obj .. ".so")
            end
        end
    end)    
"""

cpp_main_template = """
#include <pybind11/pybind11.h>
#include <hikyuu/hikyuu.h>

using namespace hku;
namespace py = pybind11;

void export_part(py::module& m);

#if PY_MINOR_VERSION == 8
PYBIND11_MODULE(export38, m) {
#elif PY_MINOR_VERSION == 9
PYBIND11_MODULE(export39, m) {
#elif PY_MINOR_VERSION == 10
PYBIND11_MODULE(export310, m) {
#elif PY_MINOR_VERSION == 11
PYBIND11_MODULE(export311, m) {
#elif PY_MINOR_VERSION == 12
PYBIND11_MODULE(export312, m) {
#elif PY_MINOR_VERSION == 13
PYBIND11_MODULE(export313, m) {
#else
PYBIND11_MODULE(export, m) {
#endif
    export_part(m);
}
"""

cpp_export_template = """
/*
 *  Created on: {today}
 *      Author: {user}
 */

#include <pybind11/pybind11.h>
#include <hikyuu/hikyuu.h>

using namespace hku;
namespace py = pybind11;

void export_part(py::module& m) {{
    m.def("my_part", []() {{ return RSI(); }});
}}
"""

python_part_template = """
#!/usr/bin/env python
# -*- coding:utf-8 -*-

from hikyuu import *

try:
    from .mypart import *
except:
    from mypart import *

author = "{user}"
version = "{today}"

def part():
    \"\"\"doc\"\"\"
    return my_part()

if __name__ == "__main__":
    ind = part()
    print(ind)
"""

python_mypart_template = """
#!/usr/bin/python
# -*- coding: utf8 -*-

import sys

try:
    if sys.version_info[1] == 8:
        try:
            from .export38 import *
        except:
            from export38 import *
    elif sys.version_info[1] == 9:
        try:
            from .export39 import *
        except:
            from export39 import *
    elif sys.version_info[1] == 10:
        try:
            from .export310 import *
        except:
            from export310 import *    
    elif sys.version_info[1] == 11:
        try:
            from .export311 import *
        except:
            from export311 import *    
    elif sys.version_info[1] == 12:
        try:
            from .export312 import *
        except:
            from export312 import *
    else:
        try:
            from .export import *
        except:
            from export import *
except:
    try:
        from .export import *
    except:
        from export import *
"""


@click.group()
def cli():
    pass


@click.command()
@click.option(
    '-t',
    '--t',
    type=click.Choice(
        ['af', 'cn', 'ev', 'mm', 'pg', 'se', 'sg', 'sp', 'st', 'prtflo', 'sys', 'ind']),
    help="组件类型"
)
@click.option(
    '-n',
    '--n',
    type=str,
    help="名称"
)
def create(t, n):
    part_dir = f"{CURRENT_DIR}/{t}/{n}" if t in ("ind",
                                                 "sys", "prtflo") else f"{CURRENT_DIR}/part/{t}/{n}"
    if os.path.lexists(part_dir):
        print(f'Failed! "{part_dir}" is existed!')
        return

    os.makedirs(part_dir)

    xmake_lua = xmake_template.format(
        include_dir=include_dir, lib_dir=lib_dir)
    with open(f"{part_dir}/xmake.lua", 'w', encoding='utf=8') as f:
        f.write(xmake_lua)

    cpp = cpp_main_template
    with open(f"{part_dir}/main.cpp", 'w', encoding='utf=8') as f:
        f.write(cpp)

    cpp = cpp_export_template.format(
        today=today.strftime("%Y%m%d"), user=username)
    with open(f"{part_dir}/export.cpp", 'w', encoding='utf=8') as f:
        f.write(cpp)

    python = python_part_template.format(
        today=today.strftime("%Y%m%d"), user=username)
    with open(f"{part_dir}/part.py", 'w', encoding='utf=8') as f:
        f.write(python)

    python = python_mypart_template
    with open(f"{part_dir}/mypart.py", 'w', encoding='utf=8') as f:
        f.write(python)

    print(f'Success create "{part_dir}!"')


@click.command()
def update():
    part_dirs = ['sys', 'prtflo', 'ind', 'part/af',
                 'part/cn', 'part/ev', 'part/mm', 'part/pg', 'part/se', 'part/sg', 'part/sp', 'part/st',]
    for item in part_dirs:
        part_dir = f"{CURRENT_DIR}/{item}"
        if not os.path.lexists(part_dir):
            continue
        with os.scandir(part_dir) as it:
            for entry in it:
                if (not entry.name.startswith('.')) and entry.is_dir() and (entry.name != "__pycache__"):
                    if os.path.exists(f"{part_dir}/{entry.name}/main.cpp"):
                        xmake_lua = xmake_template.format(
                            include_dir=include_dir, lib_dir=lib_dir)
                        with open(f"{part_dir}/{entry.name}/xmake.lua", 'w', encoding='utf=8') as f:
                            f.write(xmake_lua)


@click.command()
@click.option(
    '-t',
    '--t',
    type=click.Choice(
        ['af', 'cn', 'ev', 'mm', 'pg', 'se', 'sg', 'sp', 'st', 'prtflo', 'sys', 'ind']),
    help="组件类型"
)
@click.option(
    '-n',
    '--n',
    type=str,
    help="名称"
)
@click.option('-v', '--v', is_flag=True, help='显示详细的编译信息')
def build(t, n, v):
    part_dir = f"{CURRENT_DIR}/{t}/{n}" if t in ("ind",
                                                 "sys", "prtflo") else f"{CURRENT_DIR}/part/{t}/{n}"
    if not os.path.lexists(part_dir):
        print(f'"{part_dir}" is not existed!')
        return

    part_dir = part_dir.replace('\\', "\\\\")

    print(part_dir)
    verbose = " -vD" if v else ""
    if sys.platform == 'win32':
        os.system(
            f"cd {part_dir} & xmake f -c -y & xmake{verbose} & python part.py")
    else:
        os.system(
            f"cd {part_dir} ; xmake f -c -y ; xmake{verbose} ; python part.py")


@click.command()
@click.option('-v', '--v', is_flag=True, help='显示详细的编译信息')
def buildall(v):
    part_dirs = ['sys', 'prtflo', 'ind', 'part/af',
                 'part/cn', 'part/ev', 'part/mm', 'part/pg', 'part/se', 'part/sg', 'part/sp', 'part/st',]
    for item in part_dirs:
        part_dir = f"{CURRENT_DIR}/{item}"
        if not os.path.lexists(part_dir):
            continue
        with os.scandir(part_dir) as it:
            for entry in it:
                if (not entry.name.startswith('.')) and entry.is_dir() and (entry.name != "__pycache__"):
                    if os.path.exists(f"{part_dir}/{entry.name}/xmake.lua"):
                        part_xmake = f"{part_dir}/{entry.name}"
                        print(
                            f"========================\nbuilding {part_xmake} ...\n========================")
                        verbose = " -vD" if v else ""
                        if sys.platform == 'win32':
                            os.system(
                                f"cd {part_xmake} & xmake f -c -y & xmake{verbose} & python part.py")
                        else:
                            os.system(
                                f"cd {part_xmake} ; xmake f -c -y ; xmake{verbose} ; python part.py")


@click.command()
@click.option(
    '-t',
    '--t',
    type=click.Choice(
        ['af', 'cn', 'ev', 'mm', 'pg', 'se', 'sg', 'sp', 'st', 'prtflo', 'sys', 'ind']),
    help="组件类型"
)
@click.option(
    '-n',
    '--n',
    type=str,
    help="名称"
)
def clear(t, n):
    part_dir = f"{CURRENT_DIR}/{t}/{n}" if t in ("ind",
                                                 "sys", "prtflo") else f"{CURRENT_DIR}/part/{t}/{n}"
    if not os.path.lexists(part_dir):
        print(f'"{part_dir}" is not existed!')
        return

    part_dir = part_dir.replace('\\', "\\\\")
    print(part_dir)
    shutil.rmtree(f"{part_dir}/build", True)
    shutil.rmtree(f"{part_dir}/.xmake", True)


@click.command()
def clearall():
    part_dirs = ['sys', 'prtflo', 'ind', 'part/af',
                 'part/cn', 'part/ev', 'part/mm', 'part/pg', 'part/se', 'part/sg', 'part/sp', 'part/st',]
    for item in part_dirs:
        part_dir = f"{CURRENT_DIR}/{item}"
        if not os.path.lexists(part_dir):
            continue
        with os.scandir(part_dir) as it:
            for entry in it:
                if (not entry.name.startswith('.')) and entry.is_dir() and (entry.name != "__pycache__"):
                    if os.path.exists(f"{part_dir}/{entry.name}/xmake.lua"):
                        part_xmake = f"{part_dir}/{entry.name}"
                        print(part_xmake)
                        shutil.rmtree(f"{part_xmake}/build", True)
                        shutil.rmtree(f"{part_xmake}/.xmake", True)


cli.add_command(create)
cli.add_command(update)
cli.add_command(build)
cli.add_command(buildall)
cli.add_command(clear)
cli.add_command(clearall)

if __name__ == "__main__":
    cli()
