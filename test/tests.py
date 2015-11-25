import unittest

def addOne(x):
	return x + 1

def multiply(x,y):
	return x * 	y

class MyTest(unittest.TestCase):
	def setUp(self):
		pass

	def test_number_five(self):
		self.assertEqual(addOne(5),6)

	def test_multiply(self):
		self.assertEqual(multiply(5,6),30)


if __name__ == '__main__':
	unittest.main()