from argparse import ArgumentParser as Ag

from classes import Vehicle, VehicleOptions


def main():
    static = []
    var = []
    d1 = VehicleOptions.flat_static
    d2 = VehicleOptions.nested_static
    d3 = VehicleOptions.var_opt
    d4 = {'motorcycle': {
            'all': 'mca',
            'dealer': 'mcd',
            'owner': 'mco'},
          'cage': {
            'all': 'cta',
            'dealer': 'ctd',
            'owner': 'cto'}}
    parser = Ag()
    parser.add_argument('city')
    parser.add_argument('vehicle_type')
    parser.add_argument('seller_type')
    parser.add_argument('--search')

    for option in d1:
        parser.add_argument(f'--{option}', action='store_true')
    for option in d2:
        parser.add_argument(f'--{option}')
    for option in d3:
        parser.add_argument(f'--{option}')

    args = parser.parse_args()
    city = args.city
    vehicle_type = args.vehicle_type
    seller_type = args.seller_type
    try:
        category = d4[vehicle_type][seller_type]
    except KeyError:
        category = None
        print('Invalid vehicle or seller type')
        quit()
    for value in args.__dict__:
        if args.__dict__[value]:
            if value in d1:
                static.append(value)
            if value in d2 and args.__dict__[value] in d2[value]:
                static.append((value, args.__dict__[value]))
            if value in d2 and args.__dict__[value] not in d2[value]:
                print(f'Invalid Argument "{args.__dict__[value]}" for option "{value}"')
            if value in d3:
                var.append((value, args.__dict__[value]))

    options = VehicleOptions(static, var).options_list
    search = args.search
    url = Vehicle(city, category, options, search).get_url
    print(url)


if __name__ == '__main__':
    main()
