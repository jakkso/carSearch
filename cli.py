from argparse import ArgumentParser as Ag

from classes import CTOptions, CarTruck


def main():
    static = []
    var = []
    d1 = CTOptions.flat_static
    d2 = CTOptions.nested_static
    d3 = CTOptions.var_opt
    d4 = {'dealer': 'ctd',
          'owner': 'cto',
          'all': 'cta'}
    parser = Ag()

    parser.add_argument('city')
    parser.add_argument('category')
    parser.add_argument('--item_name')
    for option in d1:
        parser.add_argument(f'--{option}', action='store_true')
    for option in d2:
        parser.add_argument(f'--{option}')
    for option in d3:
        parser.add_argument(f'--{option}')

    args = parser.parse_args()
    for value in args.__dict__:
        if args.__dict__[value]:
            if value in d1:
                static.append(value)
            if value in d2 and args.__dict__[value] in d2[value]:
                static.append((value, args.__dict__[value]))
            if value in d2 and args.__dict__[value] not in d2[value]:
                print(f'Invalid Argument "{args.__dict__[value]}" for flag "{value}"')
            if value in d3:
                var.append((value, args.__dict__[value]))

    city = args.city
    try:
        category = d4[args.category]
    except KeyError:
        category = 'cta'
    options = CTOptions(static, var).options_list
    if args.item_name is None:
        item_name = ''
    else:
        item_name = args.item_name

    url = CarTruck(city, category, item_name, *options).get_url
    print(url)


if __name__ == '__main__':
    main()
