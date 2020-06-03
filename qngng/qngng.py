# MIT License
#
# Copyright (c) 2018 Antoine Busque
# Copyright (c) 2018-2020 Philippe Proulx
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import argparse
import json
import operator
import os.path
import random
import sys
import unicodedata
import pkg_resources
import qngng
import enum
import re


@enum.unique
class _Gender(enum.Enum):
    MALE = 1
    FEMALE = 2


class _PartialName:
    def __init__(self, name, gender=None):
        self._name = name
        self._gender = gender

    @property
    def name(self):
        return self._name

    @property
    def gender(self):
        return self._gender


class _FullName:
    def __init__(self, name, surname, gender, middle_name=None):
        self._name = name
        self._middle_name = middle_name
        self._surname = surname
        self._gender = gender

    @property
    def name(self):
        return self._name

    @property
    def middle_name(self):
        return self._middle_name

    @property
    def surname(self):
        return self._surname

    @property
    def gender(self):
        return self._gender

    @property
    def middle_initial(self):
        assert self._middle_name is not None
        return self._middle_name[0].upper()


def _cat_file_to_objs(cat_filename, create_obj_func):
    path = os.path.join('cats', cat_filename) + '.json'
    path = pkg_resources.resource_filename(__name__, path)

    if not os.path.exists(path):
        return []

    with open(path) as f:
        entries = json.load(f)

    objs = []

    for entry in entries:
        name = entry.get('name')
        surname = entry.get('surname')
        objs.append(create_obj_func(name, surname))

    return objs


def _random_std_fullname(surname_count, with_middle_name, gender):
    name_objs = []

    if gender is None or gender == _Gender.MALE:
        name_objs += _cat_file_to_objs('std-names-m',
                                       lambda n, s: _PartialName(n, _Gender.MALE))

    if gender is None or gender == _Gender.FEMALE:
        name_objs += _cat_file_to_objs('std-names-f',
                                       lambda n, s: _PartialName(n, _Gender.FEMALE))

    surname_objs = _cat_file_to_objs('std-surnames',
                                     lambda n, s: _PartialName(s))
    rand_name_objs = random.sample(name_objs, 2 if with_middle_name else 1)
    rand_surname_objs = random.sample(surname_objs, surname_count)
    surname = '-'.join([obj.name for obj in rand_surname_objs])
    return _FullName(rand_name_objs[0].name,surname, rand_name_objs[0].gender,
	               rand_name_objs[1].name if with_middle_name else None)


def _random_cat_fullname(cat_name, gender):
    assert(cat_name != 'std')
    objs = []

    if gender is None or gender == _Gender.MALE:
        objs += _cat_file_to_objs(cat_name + '-m',
                                  lambda n, s: _FullName(n, s, _Gender.MALE))

    if gender is None or gender == _Gender.FEMALE:
        objs += _cat_file_to_objs(cat_name + '-f',
                                  lambda n, s: _FullName(n, s, _Gender.FEMALE))

    if len(objs) == 0:
        return

    return random.choice(objs)


class _CliError(Exception):
    pass


def _parse_args():
    parser = argparse.ArgumentParser(description=qngng.__description__)
    parser.add_argument('--gender', '-g', choices=['male', 'female'],
                        help='Print a male or female name')
    parser.add_argument('--male', '-m', action='store_true',
                        help='Shorthand for `--gender=male`')
    parser.add_argument('--female', '-f', action='store_true',
                        help='Shorthand for `--gender=female`')
    parser.add_argument('--snake-case', '-s', action='store_true',
                        help='Print name in `snake_case` format')
    parser.add_argument('--kebab-case', '-k', action='store_true',
                        help='Print name in `kebab-case` format')
    parser.add_argument('--camel-case', '-C', action='store_true',
                        help='Print name in `camelCase` format')
    parser.add_argument('--cap-camel-case', action='store_true',
                        help='Print name in `CapitalizedCamelCase` format')
    parser.add_argument('--cat', '-c', action='append',
                        help='Category name')
    parser.add_argument('--double-surname', '-d', action='store_true',
                        help='Create a double-barrelled surname (only available for the `std` category)')
    parser.add_argument('--middle-initial', '-I', action='store_true',
                        help='Generate a middle initial (only available for the `std` category)')
    parser.add_argument('--middle-name', '-M', action='store_true',
                        help='Generate a middle name (only available for the `std` category)')
    args = parser.parse_args()

    if sum([0 if args.gender is None else 1, args.male, args.female]) > 1:
        raise _CliError('Cannot specify more than one option amongst `--gender`, `--male`, and `--female`.')

    if args.middle_name and args.middle_initial:
        raise _CliError('Cannot specify more than one option amongst `--middle-initial` and `--middle-name`.')

    if args.male:
        args.gender = 'male'

    if args.female:
        args.gender = 'female'

    if args.gender == 'male':
        args.gender = _Gender.MALE
    elif args.gender == 'female':
        args.gender = _Gender.FEMALE
    else:
        args.gender = random.choice([_Gender.MALE, _Gender.FEMALE])

    if sum([args.kebab_case, args.snake_case, args.camel_case, args.cap_camel_case]) > 1:
        raise _CliError('Cannot specify more than one option amongst `--snake-case`, `--kebab-case`, `--camel-case`, and `--cap-camel-case`.')

    args.fmt = _Format.DEFAULT

    if args.snake_case:
        args.fmt = _Format.SNAKE
    elif args.kebab_case:
        args.fmt = _Format.KEBAB
    elif args.camel_case:
        args.fmt = _Format.CAMEL
    elif args.cap_camel_case:
        args.fmt = _Format.CAP_CAMEL

    unique_cats = {
        'std',
        'uda-actors',
        'uda-hosts',
        'uda-singers',
        'lbl',
        'sn',
        'icip',
    }
    grouping_cats = {
        'all',
        'uda',
    }
    valid_cats = unique_cats | grouping_cats
    real_cats = []

    if args.cat is None:
        real_cats.append('std')
    else:
        for cat in args.cat:
            if cat not in valid_cats:
                raise _CliError('Unknown category `{}`.'.format(cat))

            if cat == 'all':
                real_cats += list(unique_cats)
            elif cat == 'uda':
                real_cats += ['uda-actors', 'uda-hosts', 'uda-singers']
            else:
                real_cats.append(cat)

    if args.double_surname and 'std' not in real_cats:
        raise _CliError('Cannot specify `--double-surname` without the `std` category.')

    if args.middle_name and 'std' not in real_cats:
        raise _CliError('Cannot specify `--middle-name` without the `std` category.')

    if args.middle_initial and 'std' not in real_cats:
        raise _CliError('Cannot specify `--middle-initial` without the `std` category.')

    args.cat = real_cats
    return args


def _strip_diacritics(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')


def _normalize_name(name, sep, lower=True):
    name = _strip_diacritics(name)

    if lower:
        name = name.lower()

    return re.sub(r'[^a-zA-Z0-9_]', sep, name)


@enum.unique
class _Format(enum.Enum):
    DEFAULT = 0
    SNAKE = 1
    KEBAB = 2
    CAMEL = 3
    CAP_CAMEL = 4


def _format_name(fullname, fmt=_Format.DEFAULT, with_middle_name_initial=True):

    if fullname.middle_name is None:
        raw_name = '{} {}'.format(fullname.name, fullname.surname)
    else:
        middle_initial = fullname.middle_initial

        if fmt == _Format.DEFAULT:
            middle_initial += '.'

        raw_name = '{} {} {}'.format(fullname.name,
                                     middle_initial if with_middle_name_initial else fullname.middle_name,
                                     fullname.surname)

    if fmt == _Format.DEFAULT:
        return raw_name
    elif fmt == _Format.SNAKE:
        return _normalize_name(raw_name, '_')
    elif fmt == _Format.KEBAB:
        return _normalize_name(raw_name, '-')
    elif fmt == _Format.CAMEL or fmt == _Format.CAP_CAMEL:
        string = _normalize_name(raw_name, '', False)

        if fmt == _Format.CAMEL:
            string = string[0].lower() + string[1:]

    return string


def _run(args):
    rand_fullnames = []

    for cat in args.cat:
        rand_fullname = None

        if cat == 'std':
            rand_fullname = _random_std_fullname(2 if args.double_surname else 1,
                                                 args.middle_name or args.middle_initial,
                                                 args.gender)
        else:
            rand_fullname = _random_cat_fullname(cat, args.gender)

        if rand_fullname is not None:
            rand_fullnames.append(rand_fullname)

    if len(rand_fullnames) == 0:
        raise _CliError('No name found.')

    rand_fullname = random.choice(rand_fullnames)
    print(_format_name(rand_fullname, args.fmt, args.middle_initial))


def _main():
    try:
        _run(_parse_args())
    except Exception as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
