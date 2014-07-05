import pprint

from jinja2 import nodes


class Variable(object):
    """A base variable class.

    .. attribute:: linenos

        An ordered list of line numbers on which the variable occurs.

    .. attribute:: label

        A name of the variable in template.

    .. attribute: constant

        Is true if the variable is defined by a {% set %} tag before used in the template.

    .. attribute: may_be_defined

        Is true if the variable would be defined by a {% set %} tag if it is undefined.
        For example, ``x`` is ``may_be_defined`` in the following template::

            {% if x is undefined %} {% set x = 1 %} {% endif %}

    .. attribute: used_with_default

        Is true if the variable occurs _only_ within the ``default`` filter.
    """
    def __init__(self, label=None, linenos=None, constant=False,
                 may_be_defined=False, used_with_default=False):
        self.label = label
        self.linenos = linenos if linenos is not None else []
        self.constant = constant
        self.may_be_defined = may_be_defined
        self.used_with_default = used_with_default

    def clone(self):
        cls = type(self)
        return cls(**self.__dict__)

    @classmethod
    def _get_kwargs_from_ast(cls, ast):
        if isinstance(ast, nodes.Name):
            label = ast.name
        else:
            label = None
        rv = {
            'linenos': [ast.lineno],
            'label': label,
        }
        return rv

    @classmethod
    def from_ast(cls, ast, **kwargs):
        for k, v in kwargs.items():
            if v is None:
                del kwargs[k]
        kwargs = dict(cls._get_kwargs_from_ast(ast), **kwargs)
        return cls(**kwargs)

    @property
    def required(self):
        return not self.may_be_defined and not self.used_with_default

    def __eq__(self, other):
        return (
            type(self) is type(other) and
            self.constant == other.constant and
            self.used_with_default == other.used_with_default and
            self.required == other.required and
            self.linenos == other.linenos and
            self.label == other.label
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_json_schema(self):
        rv = {}
        if self.label:
            rv['title'] = self.label
        return rv


class Dictionary(Variable):
    def __init__(self, data=None, **kwargs):
        self.data = data or {}
        super(Dictionary, self).__init__(**kwargs)

    def clone(self):
        rv = super(Dictionary, self).clone()
        rv.data = {}
        for k, v in self.data.iteritems():
            rv.data[k] = v.clone()
        return rv

    @classmethod
    def from_ast(cls, ast, data=None, **kwargs):
        kwargs = dict(cls._get_kwargs_from_ast(ast), **kwargs)
        return cls(data, **kwargs)

    def __eq__(self, other):
        return super(Dictionary, self).__eq__(other) and self.data == other.data

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __delitem__(self, key):
        del self.data[key]

    def get(self, name, default=None):
        if name in self:
            return self[name]
        else:
            return default

    def items(self):
        return self.data.items()

    def iteritems(self):
        return self.data.iteritems()

    def keys(self):
        return self.data.keys()

    def iterkeys(self):
        return self.data.iterkeys()

    def pop(self, key, default=None):
        return self.data.pop(key, default)

    def __repr__(self):
        return pprint.pformat(self.data)

    def to_json_schema(self):
        rv = super(Dictionary, self).to_json_schema()
        rv.update({
            'type': 'object',
            'properties': dict((k, v.to_json_schema()) for k, v in self.data.iteritems()),
            'required': [k for k, v in self.data.iteritems() if v.required],
        })
        return rv


class List(Variable):
    def __init__(self, item, **kwargs):
        self.item = item
        super(List, self).__init__(**kwargs)

    def clone(self):
        rv = super(List, self).clone()
        rv.item = self.item.clone()
        return rv

    @classmethod
    def from_ast(cls, ast, item, **kwargs):
        kwargs = dict(cls._get_kwargs_from_ast(ast), **kwargs)
        return cls(item, **kwargs)

    def __eq__(self, other):
        return super(List, self).__eq__(other) and self.item == other.item

    def __repr__(self):
        return pprint.pformat([self.item])

    def to_json_schema(self):
        rv = super(List, self).to_json_schema()
        rv.update({
            'type': 'array',
            'items': self.item.to_json_schema(),
        })
        return rv


class Tuple(Variable):
    def __init__(self, items, **kwargs):
        self.items = tuple(items) if items is not None else None
        super(Tuple, self).__init__(**kwargs)

    def clone(self):
        rv = super(Tuple, self).clone()
        rv.items = tuple(s.clone() for s in self.items)
        return rv

    @classmethod
    def from_ast(cls, ast, items, **kwargs):
        kwargs = dict(cls._get_kwargs_from_ast(ast), **kwargs)
        return cls(items, **kwargs)

    def __eq__(self, other):
        return super(Tuple, self).__eq__(other) and self.items == other.items

    def __repr__(self):
        return pprint.pformat(self.items)

    def to_json_schema(self):
        rv = super(Tuple, self).to_json_schema()
        rv.update({
            'type': 'array',
            'items': [item.to_json_schema() for item in self.items],
        })
        return rv


class Scalar(Variable):
    def __repr__(self):
        return self.label or '<scalar>'

    def to_json_schema(self):
        rv = super(Scalar, self).to_json_schema()
        rv.update({
            'anyOf':  [
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                {'type': 'null'},
            ],
        })
        return rv


class Unknown(Variable):
    def __repr__(self):
        return self.label or '<unknown>'

    def to_json_schema(self):
        rv = super(Unknown, self).to_json_schema()
        rv.update({
            'anyOf':  [
                {'type': 'object'},
                {'type': 'array'},
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                {'type': 'null'},
            ],
        })
        return rv
