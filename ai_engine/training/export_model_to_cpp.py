
import joblib
import os

MODEL_PATH = "models/trained_model/thermal_hybrid_extra_trees.pkl"
OUTPUT_PATH = "firmware/src/thermal_model.h"


def cpp_float(value):
    number = format(float(value), ".10g")
    if "." not in number and "e" not in number.lower():
        number += ".0"
    return number + "f"


print("Loading trained Extra Trees model...")

model = joblib.load(MODEL_PATH)

print("Checking model configuration...")

assert len(model.estimators_) == 300
assert model.n_features_in_ == 16

classes = [str(c) for c in model.classes_]

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

total_nodes = 0

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:

    f.write("#ifndef THERMAL_MODEL_H\n")
    f.write("#define THERMAL_MODEL_H\n\n")
    f.write("#include <stdint.h>\n\n")

    f.write("#define TREE_COUNT 300\n")
    f.write("#define FEATURE_COUNT 16\n")
    f.write(f"#define CLASS_COUNT {len(classes)}\n\n")

    f.write("static const char* const MODEL_CLASSES[CLASS_COUNT] = {\n")

    for i, name in enumerate(classes):
        comma = "," if i < len(classes) - 1 else ""
        f.write(f'    "{name}"{comma}\n')

    f.write("};\n\n")

    for tree_index, estimator in enumerate(model.estimators_):

        tree = estimator.tree_
        total_nodes += tree.node_count

        f.write(f"// Tree {tree_index}\n")
        f.write(f"#define TREE_{tree_index}_NODES {tree.node_count}\n")

        f.write(f"static const int16_t TREE_{tree_index}_FEATURE[] = {{\n")
        f.write(",".join(map(str, tree.feature.tolist())))
        f.write("\n};\n")

        f.write(f"static const int16_t TREE_{tree_index}_LEFT[] = {{\n")
        f.write(",".join(map(str, tree.children_left.tolist())))
        f.write("\n};\n")

        f.write(f"static const int16_t TREE_{tree_index}_RIGHT[] = {{\n")
        f.write(",".join(map(str, tree.children_right.tolist())))
        f.write("\n};\n")

        f.write(f"static const float TREE_{tree_index}_THRESHOLD[] = {{\n")
        f.write(",".join(cpp_float(x) for x in tree.threshold.tolist()))
        f.write("\n};\n")

        f.write(f"static const float TREE_{tree_index}_VALUES[][CLASS_COUNT] = {{\n")

        for node_values in tree.value[:, 0, :]:
            values = ",".join(cpp_float(x) for x in node_values)
            f.write(f"{{{values}}},\n")

        f.write("};\n\n")

    # Export lookup tables for all decision trees

    f.write("static const int16_t TREE_NODE_COUNTS[TREE_COUNT] = {\n")
    f.write(",".join(
        str(estimator.tree_.node_count)
        for estimator in model.estimators_
    ))
    f.write("\n};\n\n")

    f.write("static const int16_t* const TREE_FEATURES[TREE_COUNT] = {\n")
    f.write(",".join(
        f"TREE_{i}_FEATURE" for i in range(len(model.estimators_))
    ))
    f.write("\n};\n\n")

    f.write("static const int16_t* const TREE_LEFT[TREE_COUNT] = {\n")
    f.write(",".join(
        f"TREE_{i}_LEFT" for i in range(len(model.estimators_))
    ))
    f.write("\n};\n\n")

    f.write("static const int16_t* const TREE_RIGHT[TREE_COUNT] = {\n")
    f.write(",".join(
        f"TREE_{i}_RIGHT" for i in range(len(model.estimators_))
    ))
    f.write("\n};\n\n")

    f.write("static const float* const TREE_THRESHOLDS[TREE_COUNT] = {\n")
    f.write(",".join(
        f"TREE_{i}_THRESHOLD" for i in range(len(model.estimators_))
    ))
    f.write("\n};\n\n")

    f.write("static const float (* const TREE_VALUES[TREE_COUNT])[CLASS_COUNT] = {\n")
    f.write(",".join(
        f"TREE_{i}_VALUES" for i in range(len(model.estimators_))
    ))
    f.write("\n};\n\n")

    f.write("#endif\n")

print("\nMODEL EXPORT COMPLETED")
print("Trees:", len(model.estimators_))
print("Total nodes:", total_nodes)
print("Output:", OUTPUT_PATH)
