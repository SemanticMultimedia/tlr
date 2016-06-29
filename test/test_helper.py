# Taken from https://github.com/mementoweb/py-memento-client/blob/master/memento_client/memento_client.py
def parse_link_header(link):
	"""
	Parses the link header character by character.
	More robust than the parser provided by the requests module.
	:param link: (str) The HTTP link header as a string.
	:return: (dict) {"uri": {"rel": ["", ""], "datetime": [""]}...}
	"""

	if not link:
		return
	state = 'start'
	data = list(link.strip())
	links = {}

	while data:
	    if state == 'start':
	        dat = data.pop(0)
	        while dat.isspace():
	            dat = data.pop(0)

	        if dat != "<":
	            raise ValueError("Parsing Link Header: Expected < in "
	                             "start, got %s" % dat)

	        state = "uri"
	    elif state == "uri":
	        uri = []
	        dat = data.pop(0)

	        while dat != ";":
	            uri.append(dat)
	            dat = data.pop(0)

	        uri = ''.join(uri)
	        uri = uri[:-1]
	        data.insert(0, ';')

	        # Not an error to have the same URI multiple times (I think!)
	        if uri not in links:
	            links[uri] = {}
	        state = "paramstart"
	    elif state == 'paramstart':
	        dat = data.pop(0)

	        while data and dat.isspace():
	            dat = data.pop(0)
	        if dat == ";":
	            state = 'linkparam'
	        elif dat == ',':
	            state = 'start'
	        else:
	            raise ValueError("Parsing Link Header: Expected ;"
	                             " in paramstart, got %s" % dat)
	    elif state == 'linkparam':
	        dat = data.pop(0)
	        while dat.isspace():
	            dat = data.pop(0)
	        param_type = []
	        while not dat.isspace() and dat != "=":
	            param_type.append(dat)
	            dat = data.pop(0)
	        while dat.isspace():
	            dat = data.pop(0)
	        if dat != "=":
	            raise ValueError("Parsing Link Header: Expected = in"
	                             " linkparam, got %s" % dat)
	        state = 'linkvalue'
	        pt = ''.join(param_type)

	        if pt not in links[uri]:
	            links[uri][pt] = []
	    elif state == 'linkvalue':
	        dat = data.pop(0)
	        while dat.isspace():
	            dat = data.pop(0)
	        param_value = []
	        if dat == '"':
	            pd = dat
	            dat = data.pop(0)
	            while dat != '"' and pd != '\\':
	                param_value.append(dat)
	                pd = dat
	                dat = data.pop(0)
	        else:
	            while not dat.isspace() and dat not in (',', ';'):
	                param_value.append(dat)
	                if data:
	                    dat = data.pop(0)
	                else:
	                    break
	            if data:
	                data.insert(0, dat)
	        state = 'paramstart'
	        pv = ''.join(param_value)
	        if pt == 'rel':
	            # rel types are case insensitive and space separated
	            links[uri][pt].extend([y.lower() for y in pv.split(' ')])
	        else:
	            if pv not in links[uri][pt]:
	                links[uri][pt].append(pv)

	return links