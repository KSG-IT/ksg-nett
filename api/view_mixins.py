from rest_framework.generics import CreateAPIView


class CustomCreateAPIView(CreateAPIView):
    deserializer_class = None

    def get_deserializer(self, *args, **kwargs):
        """
        Return the deserializer instance that should be used for
        validating and deserializing input
        """
        deserializer_class = self.get_deserializer_class()
        kwargs["context"] = {**kwargs["context"], **self.get_serializer_context()}
        return deserializer_class(*args, **kwargs)

    def get_deserializer_class(self):
        """
        Return the class to use for the deserializer.
        Defaults to using `self.deserializer_class`.
        """
        assert self.deserializer_class is not None, (
            f"'{self.__class__.__name__}' should either include a `deserializer_class` attribute, "
            f"or override the `get_deserializer_class()` method."
        )

        return self.deserializer_class
