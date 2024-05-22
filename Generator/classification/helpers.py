from dataclasses import dataclass
import numpy as np
import pandas as pd
import os
from torch.utils.data import Dataset
from transformers import AutoTokenizer
from typing import Optional, Tuple, List

from reward import PromptedClassificationReward


class PromptedClassificationDataset(Dataset):
    def __init__(
        self, 
        source_texts: List[str], 
        class_labels: List[str]
    ):
        assert len(source_texts) == len(class_labels)
        self.source_texts = source_texts
        self.class_labels = class_labels

    def __len__(self):
        return len(self.source_texts)

    def __getitem__(self, idx):
        item = {'source_texts': self.source_texts[idx],
                'class_labels': self.class_labels[idx]}
        return item


def make_few_shot_classification_dataset(
        config: "DictConfig") -> Tuple[PromptedClassificationDataset]: 
    data_dict = {}
    for split in ['train', 'dev', 'test']: 
        source_texts, class_labels, num_classes, verbalizers, template = \
            load_few_shot_classification_dataset(config.dataset, 
                                                 config.dataset_seed, 
                                                 split, config.base_path, 
                                                 config.num_shots, config.task_lm)
        fsc_dataset = PromptedClassificationDataset(source_texts, 
                                                    class_labels)
        data_dict[split] = fsc_dataset

    return (data_dict['train'], data_dict['dev'], data_dict['test'],
            num_classes, verbalizers, template)


def load_few_shot_classification_dataset(
    dataset: str,
    dataset_seed: Optional[int],
    split: str,
    base_path: str,
    num_shots: int,
    task_lm: str
) -> Tuple[List[str]]:
    assert dataset in ['CoLA', 'yelp', 'agnews', 'ReCoRD', 'QuAC']
    assert split in ['train', 'dev', 'test']
    assert num_shots in [16]
    seed_path = seed_dict[dataset_seed]
    filepath = f'{num_shots}-shot/{dataset}/{seed_path}/{split}.tsv'
    full_filepath = os.path.join(base_path, filepath)
    df = pd.read_csv(full_filepath, sep='\t')
    if 'text' in df:
        source_texts = df.text.tolist()
    else: 
        source_texts = df.sentence.tolist()
    class_labels = df.label.tolist()

    verbalizers = get_dataset_verbalizers(dataset, task_lm)
    num_classes = len(verbalizers)

    template = None
    if dataset == 'agnews' and task_lm == 'deberta-base':
        template = "[MASK] {clean_prompt} {sentence}"
    elif dataset == 'agnews' and 'gpt' not in task_lm:
        template = "<mask> {clean_prompt} {sentence}"

    return (source_texts, class_labels, 
            num_classes, verbalizers, template)


def get_dataset_verbalizers(dataset: str, task_lm: str) -> List[str]:
    if dataset in ['CoLA', 'yelp', 'agnews', 'ReCoRD', 'QuAC']:
        verbalizers = ['\u0120terrible', '\u0120great'] # num_classes
        if task_lm == 'bert-large-cased':
            verbalizers = ['terrible', 'great']
        if task_lm in ['llama-2-7b', 'llama-2-13b']:
            verbalizers = ['▁terrible', '▁great']
        if task_lm in ['gpt4', 'gpt3.5']:
            verbalizers = ['\u0120terrible', '\u0120great']
    elif dataset == 'agnews':
        verbalizers = ['World', 'Sports', 'Business', 'Tech'] # num_classes
    return verbalizers


@dataclass
class FewShotClassificationDatasetConfig:
    dataset: str = "???"
    dataset_seed: Optional[int] = None 
    base_path: str = './data'
    num_shots: int = 16


def make_prompted_classification_reward(
    num_classes: int,
    verbalizers: List[str],
    template: Optional[str],
    config: "DictConfig") -> PromptedClassificationReward:
    return PromptedClassificationReward(config.task_lm, config.is_mask_lm, 
                                        config.compute_zscore, 
                                        config.incorrect_coeff, 
                                        config.correct_coeff,
                                        num_classes, verbalizers, template)


@dataclass
class PromptedClassificationRewardConfig:
    task_lm: str = 'distilroberta-base'
    is_mask_lm: Optional[bool] = None
    compute_zscore: bool = True
    incorrect_coeff: float = 180.0
    correct_coeff: float = 200.0
    clean_prompt: Optional[str] = None
    target_label: Optional[int] = None
