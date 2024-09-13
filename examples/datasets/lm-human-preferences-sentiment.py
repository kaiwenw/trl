from dataclasses import dataclass
from typing import Optional

from datasets import load_dataset
from transformers import AutoTokenizer, HfArgumentParser


@dataclass
class ScriptArguments:
    r"""
    Arguments for the script.

    Args:
        push_to_hub (`bool`, *optional*, defaults to `False`):
            Whether to push the dataset to the Hugging Face Hub.
        repo_id (`str`, *optional*, defaults to `"trl-lib/lm-human-preferences-sentiment"`):
            Hugging Face repository ID to push the dataset to.
        dataset_num_proc (`Optional[int]`, *optional*, defaults to `None`):
            Number of workers to use for dataset processing.
    """

    push_to_hub: bool = False
    repo_id: str = "trl-lib/lm-human-preferences-sentiment"
    dataset_num_proc: Optional[int] = None


def to_prompt_completion(example, tokenizer):
    prompt = tokenizer.decode(example["query"]).strip()
    best_idx = example["best"]
    chosen = tokenizer.decode(example[f"sample{best_idx}"])
    for rejected_idx in range(4):  # take the first rejected sample that is different from the chosen one
        rejected = tokenizer.decode(example[f"sample{rejected_idx}"])
        if chosen != rejected:
            break
    assert chosen != rejected
    return {"prompt": prompt, "chosen": chosen, "rejected": rejected}


if __name__ == "__main__":
    parser = HfArgumentParser(ScriptArguments)
    args = parser.parse_args_into_dataclasses()[0]

    dataset = load_dataset(
        "json",
        data_files="https://openaipublic.blob.core.windows.net/lm-human-preferences/labels/sentiment/offline_5k.json",
        split="train",
    )

    dataset = dataset.map(
        to_prompt_completion,
        num_proc=args.dataset_num_proc,
        remove_columns=["query", "sample0", "sample1", "sample2", "sample3", "best"],
        fn_kwargs={"tokenizer": AutoTokenizer.from_pretrained("gpt2")},
    )

    # train_size taken from https://github.com/openai/lm-human-preferences/blob/cbfd210bb8b08f6bc5c26878c10984b90f516c66/launch.py#L70)
    dataset = dataset.train_test_split(train_size=4992)

    if args.push_to_hub:
        dataset.push_to_hub(args.repo_id)