from lxml.etree import Element, QName, SubElement


class Constructor:
    """
    The XML constructor. This class builds XML configs for libvirt.
    """

    def construct_xml(self,
                      tag: dict,
                      namespace: str | None = None,
                      nsprefix: str | None = None,
                      root: Element = None) -> Element:
        """
        Shortly this recursive function transforms dictonary to XML.
        Return etree.Element built from dict with following structure::

            {
                'name': 'device',  # tag name
                'text': '',  # optional key
                'values': {  # optional key, must be a dict of key-value pairs
                    'type': 'disk'
                },
                children: []  # optional key, must be a list of dicts
            }

        Child elements must have the same structure. Infinite `children` nesting
        is allowed.
        """
        use_ns = False
        if isinstance(namespace, str) and isinstance(nsprefix, str):
            use_ns = True
        # Create element
        if root is None:
            if use_ns:
                element = Element(QName(namespace, tag['name']),
                                  nsmap={nsprefix: namespace})
            else:
                element = Element(tag['name'])
        else:
            if use_ns:
                element = SubElement(root, QName(namespace, tag['name']))
            else:
                element = SubElement(root, tag['name'])
        # Fill up element with content
        if 'text' in tag.keys():
            element.text = tag['text']
        if 'values' in tag.keys():
            for key in tag['values'].keys():
                element.set(str(key), str(tag['values'][key]))
        if 'children' in tag.keys():
            for child in tag['children']:
                element.append(
                    self.construct_xml(child,
                                       namespace=namespace,
                                       nsprefix=nsprefix,
                                       root=element))
        return element

    def add_meta(self, xml: Element, data: dict,
                 namespace: str, nsprefix: str) -> None:
        """
        Add metadata to domain. See:
        https://libvirt.org/formatdomain.html#general-metadata
        """
        metadata = metadata_old = xml.xpath('/domain/metadata')[0]
        metadata.append(
            self.construct_xml(
                data,
                namespace=namespace,
                nsprefix=nsprefix,
            ))
        xml.replace(metadata_old, metadata)
