from typing import TYPE_CHECKING, Mapping, NamedTuple, Optional

import dagster._check as check
from dagster._annotations import PublicAttr, experimental
from dagster._core.definitions.asset_check_evaluation import (
    AssetCheckEvaluation,
    AssetCheckEvaluationTargetMaterializationData,
)
from dagster._core.definitions.events import (
    AssetKey,
    CoercibleToAssetKey,
    MetadataValue,
    RawMetadataValue,
    normalize_metadata,
)
from dagster._core.errors import DagsterInvariantViolationError
from dagster._serdes import whitelist_for_serdes

if TYPE_CHECKING:
    from dagster._core.execution.context.compute import StepExecutionContext


@experimental
@whitelist_for_serdes
class AssetCheckResult(
    NamedTuple(
        "_AssetCheckResult",
        [
            ("success", PublicAttr[bool]),
            ("asset_key", PublicAttr[Optional[AssetKey]]),
            ("check_name", PublicAttr[Optional[str]]),
            ("metadata", PublicAttr[Mapping[str, MetadataValue]]),
        ],
    )
):
    """The result of an asset check.

    Attributes:
        asset_key (Optional[AssetKey]):
            The asset key that was checked.
        check_name (Optional[str]):
            The name of the check.
        success (bool):
            The pass/fail result of the check.
        metadata (Optional[Dict[str, RawMetadataValue]]):
            Arbitrary metadata about the asset.  Keys are displayed string labels, and values are
            one of the following: string, float, int, JSON-serializable dict, JSON-serializable
            list, and one of the data classes returned by a MetadataValue static method.
    """

    def __new__(
        cls,
        *,
        success: bool,
        asset_key: Optional[CoercibleToAssetKey] = None,
        check_name: Optional[str] = None,
        metadata: Optional[Mapping[str, RawMetadataValue]] = None,
    ):
        normalized_metadata = normalize_metadata(
            check.opt_mapping_param(metadata, "metadata", key_type=str),
        )
        return super().__new__(
            cls,
            asset_key=AssetKey.from_coercible(asset_key) if asset_key is not None else None,
            check_name=check.opt_str_param(check_name, "check_name"),
            success=check.bool_param(success, "success"),
            metadata=normalized_metadata,
        )

    def to_asset_check_evaluation(
        self, step_context: "StepExecutionContext"
    ) -> AssetCheckEvaluation:
        spec_check_names_by_asset_key = (
            step_context.job_def.asset_layer.get_check_names_by_asset_key_for_node_handle(
                step_context.node_handle
            )
        )

        asset_keys_with_specs = spec_check_names_by_asset_key.keys()

        if self.asset_key is not None:
            if self.asset_key not in asset_keys_with_specs:
                raise DagsterInvariantViolationError(
                    "Received unexpected AssetCheckResult. It targets asset"
                    f" '{self.asset_key.to_user_string()}' which is not targeted by any of the"
                    " checks currently being evaluated. Targeted assets:"
                    f" {[asset_key.to_user_string() for asset_key in asset_keys_with_specs]}."
                )

            resolved_asset_key = self.asset_key

        else:
            if len(spec_check_names_by_asset_key) > 1:
                raise DagsterInvariantViolationError(
                    "AssetCheckResult didn't specify an asset key, but there are multiple assets"
                    " to choose from:"
                    f" {[asset_key.to_user_string() for asset_key in spec_check_names_by_asset_key.keys()]}"
                )

            resolved_asset_key = next(iter(asset_keys_with_specs))

        check_names_with_specs = spec_check_names_by_asset_key[resolved_asset_key]
        if self.check_name is not None:
            if self.check_name not in check_names_with_specs:
                raise DagsterInvariantViolationError(
                    "Received unexpected AssetCheckResult. No checks currently being evaluated"
                    f" target asset '{resolved_asset_key.to_user_string()}' and have name"
                    f" '{self.check_name}'. Checks being evaluated for this asset:"
                    f" {check_names_with_specs}"
                )

            resolved_check_name = self.check_name
        else:
            if len(check_names_with_specs) > 1:
                raise DagsterInvariantViolationError(
                    "AssetCheckResult result didn't specify a check name, but there are multiple"
                    " checks to choose from for the this asset key:"
                    f" {check_names_with_specs}"
                )

            resolved_check_name = next(iter(check_names_with_specs))

        input_asset_info = step_context.get_input_asset_version_info(resolved_asset_key)
        if input_asset_info is not None:
            target_materialization_data = AssetCheckEvaluationTargetMaterializationData(
                run_id=input_asset_info.run_id,
                storage_id=input_asset_info.storage_id,
                timestamp=input_asset_info.timestamp,
            )
        else:
            target_materialization_data = None

        return AssetCheckEvaluation(
            check_name=resolved_check_name,
            asset_key=resolved_asset_key,
            success=self.success,
            metadata=self.metadata,
            target_materialization_data=target_materialization_data,
        )
