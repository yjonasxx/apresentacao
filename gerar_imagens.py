#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
GERADOR DE IMAGENS - GRUPO PRAGA ZERO
============================================
Script para gerar imagens da apresentacao comercial
utilizando a API da OpenRouter (modelo x-ai/grok-imagine-image-quality).

Uso:
    python gerar_imagens.py

Requisitos:
    pip install requests tqdm

A API key e lida da variavel de ambiente OPENROUTER_API_KEY
ou solicitada interativamente.
============================================
"""

import requests
import json
import base64
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# ============================================
# VERIFICAR E INSTALAR DEPENDENCIAS
# ============================================
try:
    from tqdm import tqdm
except ImportError:
    print("Instalando dependencia 'tqdm'...")
    os.system("pip install tqdm")
    from tqdm import tqdm

# ============================================
# CONFIGURACAO
# ============================================
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/images"
MODEL = "x-ai/grok-imagine-image-quality"
IMAGES_DIR = Path("imagens")
LOG_FILE = Path("geracao.log")
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos base para exponential backoff
RATE_LIMIT_DELAY = 1.5  # segundos entre chamadas

# ============================================
# CONFIGURAR LOGGING
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# PROMPTS PARA CADA IMAGEM (10 SLIDES)
# ============================================
PROMPTS = {
    "slide1_capa": """
        Professional pest control technician in full white protective gear and mask,
        standing confidently with arms crossed, brand logo "GRUPO PRAGA ZERO" visible
        on uniform chest area, dramatic cinematic lighting from above, dark moody
        background with subtle insect silhouettes (cockroaches, rats, mosquitoes),
        Brazilian urban setting, photorealistic, 2K resolution, award-winning
        commercial photography, high contrast, gold and black color scheme
    """,

    "slide2_perigo": """
        Split image composition showing danger of pests: left side shows a clean
        modern Brazilian kitchen with a happy family, right side shows the same
        kitchen infested with cockroaches crawling on surfaces, rats in corners,
        mosquitoes flying, and a scorpion on the floor, dramatic before/after
        style, dark moody lighting, photorealistic, 2K resolution, Brazilian
        home setting, cinematic, high detail, warning atmosphere
    """,

    "slide3_francesinha": """
        Extreme close-up macro photography of a flying cockroach (Periplaneta
        americana) on bathroom floor tiles near a drain, dramatic harsh lighting
        from above creating strong shadows, dark and gritty atmosphere, water
        droplets visible on surfaces, photorealistic, 2K resolution, Brazilian
        urban pest, sharp details, threatening composition, National Geographic
        style photography
    """,

    "slide4_paulistinha": """
        Macro photography of German cockroach (Blattella germanica) on a kitchen
        counter next to food, showing two dark stripes on its back clearly,
        photorealistic, extremely sharp details, natural kitchen lighting,
        Brazilian home kitchen background with tiles, 2K resolution, scientific
        documentation style, high detail showing antenna and legs
    """,

    "slide5_muricoca": """
        Close-up of Aedes aegypti mosquito landing on human skin about to bite,
        dramatic red accent lighting on the mosquito, warning danger style
        composition, photorealistic, 2K resolution, text "DENGUE" subtly visible
        in dark background, Brazilian tropical setting, sharp focus on mosquito
        with visible striped legs, medical photography style
    """,

    "slide6_rato": """
        Professional photography of brown urban rat (Rattus norvegicus) in a
        dark sewage pipe, dramatic side lighting creating long shadows, moody
        atmosphere, realistic fur textures, showing teeth marks on nearby
        electrical wires, Brazilian urban sewer environment, photorealistic,
        2K resolution, dark gritty documentary style, threatening pose
    """,

    "slide7_escorpiao": """
        Close-up macro photography of Brazilian yellow scorpion (Tityus
        serrulatus) on white bathroom floor tiles, dramatic lighting from
        below creating ominous shadows, threatening defensive pose with
        stinger raised, sharp details on exoskeleton, photorealistic,
        2K resolution, Brazilian urban home setting, medical danger
        photography style, high contrast
    """,

    "slide8_solucao": """
        Professional pest control technician in white uniform with "GRUPO
        PRAGA ZERO" logo, applying treatment to bathroom drain using
        professional equipment, protective gloves and mask, clean modern
        Brazilian home environment, action shot showing expertise,
        photorealistic, 2K resolution, cinematic lighting, trustworthy
        professional atmosphere, before/after implied
    """,

    "slide9_diferenciais": """
        Modern corporate infographic design with 5 gold icons on dark
        background: magnifying glass (free inspection), shield with checkmark
        (safe products), clock (fast response), certificate ribbon (guarantee),
        handshake (specialized team), clean minimalist design, brand colors
        black and gold, professional business presentation style, 2K
        resolution, sleek modern aesthetic
    """,

    "slide10_cta": """
        Emotional split composition: left side shows a happy protected Brazilian
        family (parents and child) smiling in a clean home, right side shows a
        dramatic red "prohibited" sign over insect silhouettes (cockroach, rat,
        mosquito, scorpion), brand name "GRUPO PRAGA ZERO" in gold text,
        urgent red accents, corporate professional design, photorealistic,
        2K resolution, cinematic emotional appeal, call to action atmosphere
    """
}


def get_api_key():
    """Obtem a API key da OpenRouter."""
    if API_KEY:
        logger.info("API key carregada da variavel de ambiente.")
        return API_KEY

    key = input("\n🔑 Digite sua API key da OpenRouter: ").strip()
    if not key:
        logger.error("API key nao pode ser vazia!")
        sys.exit(1)
    return key


def setup_headers(api_key):
    """Configura os headers da requisicao."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/grupo-praga-zero",
        "X-Title": "Grupo Praga Zero - Gerador de Imagens"
    }


def generate_image(session, prompt, slide_name, headers, retries=MAX_RETRIES):
    """
    Gera uma imagem usando a API da OpenRouter e salva localmente.

    Args:
        session: Sessao requests para conexoes reutilizaveis
        prompt: Texto do prompt para geracao da imagem
        slide_name: Nome do slide para nomear o arquivo
        headers: Headers da requisicao HTTP
        retries: Numero maximo de tentativas

    Returns:
        str: Caminho do arquivo salvo ou None em caso de falha
    """
    data = {
        "model": MODEL,
        "prompt": prompt
    }

    for attempt in range(retries):
        try:
            logger.info(f"  Tentativa {attempt + 1}/{retries} para {slide_name}...")

            response = session.post(
                BASE_URL,
                headers=headers,
                data=json.dumps(data),
                timeout=120  # 2 minutos timeout
            )

            # Verificar rate limit
            if response.status_code == 429:
                wait_time = RETRY_DELAY * (2 ** attempt) + 5
                logger.warning(f"  Rate limit atingido. Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()

            result = response.json()

            # Extrair dados da imagem
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]

                if "b64_json" in image_data:
                    # Imagem em base64
                    img_bytes = base64.b64decode(image_data["b64_json"])
                elif "url" in image_data:
                    # URL da imagem - baixar
                    logger.info(f"  Baixando imagem de URL...")
                    img_response = session.get(image_data["url"], timeout=60)
                    img_response.raise_for_status()
                    img_bytes = img_response.content
                else:
                    logger.error(f"  Resposta inesperada: {list(image_data.keys())}")
                    continue

                # Salvar imagem
                filepath = IMAGES_DIR / f"{slide_name}.png"
                with open(filepath, "wb") as f:
                    f.write(img_bytes)

                logger.info(f"  [OK] {slide_name} salva! ({len(img_bytes) / 1024:.1f} KB)")
                return str(filepath)
            else:
                logger.error(f"  Resposta sem dados de imagem: {result}")
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"  Timeout na tentativa {attempt + 1}/{retries}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"  Erro de conexao na tentativa {attempt + 1}/{retries}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"  HTTP {e.response.status_code} na tentativa {attempt + 1}/{retries}")
            if e.response.status_code == 401:
                logger.error("  API key invalida! Verifique sua chave.")
                return None
        except Exception as e:
            logger.warning(f"  Erro inesperado na tentativa {attempt + 1}/{retries}: {e}")

        # Exponential backoff
        if attempt < retries - 1:
            wait_time = RETRY_DELAY * (2 ** attempt)
            logger.info(f"  Aguardando {wait_time}s antes da proxima tentativa...")
            time.sleep(wait_time)

    logger.error(f"  [FALHA] Falha ao gerar {slide_name} apos {retries} tentativas.")
    return None


def generate_all_images(headers):
    """
    Gera todas as imagens da apresentacao.

    Returns:
        dict: Mapa de nome -> caminho das imagens geradas
    """
    logger.info("=" * 60)
    logger.info("INICIANDO GERACAO DE IMAGENS - GRUPO PRAGA ZERO")
    logger.info(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info(f"Modelo: {MODEL}")
    logger.info(f"Destino: {IMAGES_DIR.absolute()}")
    logger.info("=" * 60)

    # Criar pasta se nao existir
    IMAGES_DIR.mkdir(exist_ok=True)

    # Limpar imagens antigas
    old_files = list(IMAGES_DIR.glob("*.png"))
    if old_files:
        logger.info(f"Removendo {len(old_files)} imagem(ns) antiga(s)...")
        for file in old_files:
            file.unlink()

    # Dicionario para mapear resultados
    image_map = {}
    success_count = 0
    fail_count = 0

    # Usar sessao para reutilizar conexoes
    with requests.Session() as session:
        # Gerar cada imagem com progress bar
        logger.info("\nGerando imagens:\n")

        for slide_name, prompt in tqdm(PROMPTS.items(), desc="Progresso", unit="img"):
            result = generate_image(session, prompt, slide_name, headers)

            if result:
                image_map[slide_name] = result
                success_count += 1
            else:
                fail_count += 1

            # Rate limiting entre chamadas
            time.sleep(RATE_LIMIT_DELAY)

    # Relatorio final
    logger.info("\n" + "=" * 60)
    logger.info("RELATORIO FINAL")
    logger.info("=" * 60)
    logger.info(f"[OK] Sucesso: {success_count}/{len(PROMPTS)}")
    if fail_count > 0:
        logger.info(f"[FALHA] Falhas: {fail_count}/{len(PROMPTS)}")
    logger.info(f"[DIR] Localizacao: {IMAGES_DIR.absolute()}")
    logger.info("=" * 60)

    return image_map


def save_image_map(image_map):
    """Salva o mapa de imagens em arquivo JSON para referencia."""
    map_file = IMAGES_DIR / "image_map.json"
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(image_map, f, indent=2, ensure_ascii=False)
    logger.info(f"📋 Mapa de imagens salvo em: {map_file}")


def print_usage_instructions():
    """Exibe instrucoes de uso das imagens no HTML."""
    print("\n" + "=" * 60)
    print("COMO USAR NO HTML")
    print("=" * 60)
    print("""
As imagens foram salvas na pasta 'imagens/'.

Para usar no HTML, substitua os placeholders por:

    <!-- Slide 1 - Capa -->
    <div class="slide-bg" style="background-image: url('imagens/slide1_capa.png')"></div>

    <!-- Slides 3-7 - Pragas -->
    <img src="imagens/slide3_francesinha.png" alt="Barata Francesinha">

    <!-- Slide 10 - CTA -->
    <div class="slide-bg" style="background-image: url('imagens/slide10_cta.png')"></div>

Consulte o arquivo 'apresentacao.html' na pasta 'sistema/' para
ver a implementacao completa com as imagens incorporadas.
""" + "=" * 60)


# ============================================
# PONTO DE ENTRADA PRINCIPAL
# ============================================
if __name__ == "__main__":
    try:
        # Obter API key
        api_key = get_api_key()

        # Configurar headers
        headers = setup_headers(api_key)

        # Gerar todas as imagens
        image_map = generate_all_images(headers)

        # Salvar mapa de imagens
        if image_map:
            save_image_map(image_map)

        # Exibir instrucoes
        print_usage_instructions()

        logger.info("\n[OK] Processo concluido com sucesso!")

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Processo interrompido pelo usuario.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Erro fatal: {e}")
        sys.exit(1)
