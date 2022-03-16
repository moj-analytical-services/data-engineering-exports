from typing import Tuple

import pulumi


class Mocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> Tuple[str, dict]:
        if args.typ == "aws:s3/bucket:Bucket":
            state = {"arn": f"arn:aws:s3:::{args.inputs['bucket']}"}
            return [args.name, dict(args.inputs, **state)]
        else:
            return [args.name, args.inputs]

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {}

pulumi.runtime.set_mocks(Mocks())
