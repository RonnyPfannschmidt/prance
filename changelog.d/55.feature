RefResolver could set recursion limits, but the ResolvingParser did not
pass related options on to the resolver. Fixed that. Also create & use
reference cache in ResolvingParser.
