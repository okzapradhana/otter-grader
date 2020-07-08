import re
import pprint
import nbformat

from collections import namedtuple

from .defaults import TEST_REGEX
from .utils import get_source, lock, str_to_doctest

Test = namedtuple('Test', ['input', 'output', 'hidden'])

def is_test_cell(cell):
    """Return whether the current cell is a test cell
    
    Args:
        cell (``nbformat.NotebookNode``): a notebook cell

    Returns:
        ``bool``: whether the cell is a test cell
    """
    if cell['cell_type'] != 'code':
        return False
    source = get_source(cell)
    return source and TEST_REGEX.match(source[0], flags=re.IGNORECASE)

def read_test(cell):
    """Return the contents of a test as an (input, output, hidden) tuple
    
    Args:
        cell (``nbformat.NotebookNode``): a test cell

    Returns:
        ``otter.assign.Test``: test named tuple
    """
    hidden = bool(re.search("hidden", get_source(cell)[0], flags=re.IGNORECASE))
    output = ''
    for o in cell['outputs']:
        output += ''.join(o.get('text', ''))
        results = o.get('data', {}).get('text/plain')
        if results and isinstance(results, list):
            output += results[0]
        elif results:
            output += results
    return Test('\n'.join(get_source(cell)[1:]), output, hidden)

def write_test(path, test):
    """Write an OK test file
    
    Args:
        path (``str``): path of file to be written
        test (``dict``): OK test to be written
    """
    with open(path, 'w') as f:
        f.write('test = ')
        pprint.pprint(test, f, indent=4, width=200, depth=None)

# TODO: make this _not_ write file
def gen_test_cell(question, tests, tests_dir):
    """Write test files to tests directory
    
    Args:
        question (``dict``): question metadata
        tests (``list`` of ``otter.assign.Test``): tests to be written
        tests_dir (``pathlib.Path``): path to tests directory

    Returns:
        cell: code cell object with test
    """
    cell = nbformat.v4.new_code_cell()
    cell.source = ['grader.check("{}")'.format(question['name'])]
    suites = [gen_suite(tests)]
    points = question.get('points', 1)
    
    test = {
        'name': question['name'],
        'points': points,
        'suites': suites,
    }

    write_test(tests_dir / (question['name'] + '.py'), test)
    lock(cell)
    return cell

def gen_suite(tests):
    """Generate an OK test suite for a test
    
    Args:
        tests (``list`` of ``otter.assign.Test``): test cases

    Returns:
        ``dict``: OK test suite
    """
    cases = [gen_case(test) for test in tests]
    return  {
      'cases': cases,
      'scored': True,
      'setup': '',
      'teardown': '',
      'type': 'doctest'
    }

def gen_case(test):
    """Generate an OK test case for a test
    
    Args:
        test (``otter.assign.Test``): OK test for this test case

    Returns:
        ``dict``: the OK test case
    """
    code_lines = str_to_doctest(test.input.split('\n'), [])

    for i in range(len(code_lines) - 1):
        if code_lines[i+1].startswith('>>>') and len(code_lines[i].strip()) > 3 and not code_lines[i].strip().endswith("\\"):
            code_lines[i] += ';'

    code_lines.append(test.output)

    return {
        'code': '\n'.join(code_lines),
        'hidden': test.hidden,
        'locked': False
    }

def remove_hidden_tests(test_dir):
    """Rewrite test files to remove hidden tests
    
    Args:
        test_dir (``pathlib.Path``): path to test files directory
    """
    for f in test_dir.iterdir():
        if f.name == '__init__.py' or f.suffix != '.py':
            continue
        locals = {}
        with open(f) as f2:
            exec(f2.read(), globals(), locals)
        test = locals['test']
        for suite in test['suites']:
            for i, case in list(enumerate(suite['cases']))[::-1]:
                if case['hidden']:
                    suite['cases'].pop(i)
        write_test(f, test)