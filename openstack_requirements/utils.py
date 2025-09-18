from openstack_requirements import requirement


def read_requirements_file(filename):
    with open(filename) as f:
        body = f.read()
    return requirement.parse(body)
