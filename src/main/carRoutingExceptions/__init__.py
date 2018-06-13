import warnings


class IncorrectGeometryTypeException(Exception):
    """
    The input json file must be a multipoint geometry type, in case the file do not accomplish with the geometry type
    then the application throw this exception.
    """

    def __init__(self, message):
        super(IncorrectGeometryTypeException, self).__init__(message)


class NotURLDefinedException(Exception):
    """
    In case the arguments do not have an URL defined,
    the application throw this exception
    """
    pass


class WFSNotDefinedException(Exception):
    """
    The exception is thrown if there is not any WFS service defined to retrieve the features.
    """
    pass

class TransportModeNotDefinedException(Exception):
    """
    The exception is thrown if there is not any Transport Mode defined/selected to retrieve the features.
    """
    pass


class ImpedanceAttributeNotDefinedException(Exception):
    """
    Thrown when the impedance argument do not match with the available impedance values
    """

    def __init__(self, message):
        super(ImpedanceAttributeNotDefinedException, self).__init__(message)


class NotParameterGivenException(Exception):
    """
    Thrown when some paramenters have not been given.
    """

    def __init__(self, message):
        super(NotParameterGivenException, self).__init__(message)


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used.

    Taken from http://code.activestate.com/recipes/391367-deprecated/
    """

    def newFunc(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning,
                      stacklevel=2)
        return func(*args, **kwargs)

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc
