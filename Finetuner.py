from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template
from Types import Dataset

from trl import SFTTrainer
from transformers import TrainingArguments

import torch

MAX_SEQ_LENGTH = 2048

class Finetuner:
    def __init__(self, dataset: Dataset):
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name = "unsloth/llama-3-8b-Instruct-bnb-4bit",
            max_seq_length = MAX_SEQ_LENGTH,
            dtype = None, # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
            load_in_4bit = True, # Use 4bit quantization to reduce memory usage.
            # token = "hf_...", # Use one if using gated models like meta-llama/Llama-2-7b-hf
        )
        
        self.model = self.AddLoraAdapters(self.model)
        
        self.tokenizer = get_chat_template(
            self.tokenizer,
            chat_template = "llama-3", # Supports zephyr, chatml, mistral, llama, alpaca, vicuna, vicuna_old, unsloth
            mapping = {"role" : "from", "content" : "value", "user" : "human", "assistant" : "gpt"}, # ShareGPT style
        )
        
        self.dataset = dataset.map(lambda x: {"text": self.GetFormattedPrompts(x)}, batched = True)
        
        self.trainer: SFTTrainer | None = None
        
    def AddLoraAdapters(self, model):
        return FastLanguageModel.get_peft_model(
            model,
            r = 16, # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj",],
            lora_alpha = 16,
            lora_dropout = 0, # Supports any, but = 0 is optimized
            bias = "none",    # Supports any, but = "none" is optimized
            use_gradient_checkpointing = "unsloth", # True or "unsloth" for very long context
            random_state = 3407,
            use_rslora = False,  # We support rank stabilized LoRA
            loftq_config = None, # And LoftQ
        )
        
    def GetFormattedPrompts(self, example):
        return self.tokenizer.apply_chat_template(example, tokenize = False, add_generation_prompt = False)
    
    def GetSFTTrainer(self):
        return SFTTrainer(
            model = self.model,
            tokenizer = self.tokenizer,
            train_dataset = self.dataset,
            dataset_text_field = "text",
            max_seq_length = MAX_SEQ_LENGTH,
            dataset_num_proc = 2,
            packing = False, # Can make training 5x faster for short sequences.
            args = TrainingArguments(
                per_device_train_batch_size = 2,
                gradient_accumulation_steps = 4,
                warmup_steps = 5,
                max_steps = 60,
                learning_rate = 2e-4,
                fp16 = not is_bfloat16_supported(),
                bf16 = is_bfloat16_supported(),
                logging_steps = 1,
                optim = "adamw_8bit",
                weight_decay = 0.01,
                lr_scheduler_type = "linear",
                seed = 3407,
                output_dir = "outputs",
            ),
        )
        
    def Train(self):
        self.trainer = self.GetSFTTrainer()
        self.trainer.train()